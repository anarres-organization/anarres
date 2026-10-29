/*
 * Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
 *
 * cmd.c - parses one command line of the script language and prints the reply.
 */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sesscache.h"

#define MAX_ARGS 4

static void reply_error(Cache *c, const char *msg)
{
    printf("error: %s\n", msg);
    c->st.errors++;
}

static int valid_id(const char *s)
{
    size_t n = strlen(s);
    size_t i;

    if (n == 0 || n > ID_MAX)
        return 0;
    for (i = 0; i < n; i++) {
        unsigned char ch = (unsigned char)s[i];
        if (!isalnum(ch) && ch != '_' && ch != '.' && ch != '-')
            return 0;
    }
    return 1;
}

/* Plain decimal, at most 9 digits. */
static int parse_number(const char *s, unsigned long *out)
{
    size_t n = strlen(s);
    size_t i;
    unsigned long v = 0;

    if (n == 0 || n > 9)
        return 0;
    for (i = 0; i < n; i++) {
        if (!isdigit((unsigned char)s[i]))
            return 0;
        v = v * 10 + (unsigned long)(s[i] - '0');
    }
    *out = v;
    return 1;
}

static void report_expired(void *ctx, const char *id)
{
    (void)ctx;
    printf("expired %s\n", id);
}

static void do_open(Cache *c, int argc, char **argv)
{
    unsigned long size = DEFAULT_SIZE;
    OpenInfo info;
    Result r;

    if (argc < 2 || argc > 3) {
        reply_error(c, "usage: open ID [SIZE]");
        return;
    }
    if (!valid_id(argv[1])) {
        reply_error(c, "bad id");
        return;
    }
    if (argc == 3 && !parse_number(argv[2], &size)) {
        reply_error(c, "bad number");
        return;
    }
    r = cache_open(c, argv[1], size, &info);
    if (r == R_FAILED) {
        reply_error(c, "open failed");
    } else if (r == R_FULL) {
        reply_error(c, "cache full");
    } else {
        if (info.evicted[0])
            printf("note: evicted %s (capacity)\n", info.evicted);
        if (info.reopened)
            printf("ok reopened %s refs=%d\n", argv[1], info.refs);
        else
            printf("ok opened %s size=%lu\n", argv[1], size);
    }
}

static void do_touch(Cache *c, int argc, char **argv)
{
    TouchMode mode = T_PLAIN;
    int pins = 0;
    Result r;

    if (argc < 2 || argc > 3) {
        reply_error(c, "usage: touch ID [pin|unpin]");
        return;
    }
    if (!valid_id(argv[1])) {
        reply_error(c, "bad id");
        return;
    }
    if (argc == 3) {
        if (strcmp(argv[2], "pin") == 0)
            mode = T_PIN;
        else if (strcmp(argv[2], "unpin") == 0)
            mode = T_UNPIN;
        else {
            reply_error(c, "usage: touch ID [pin|unpin]");
            return;
        }
    }
    r = cache_touch(c, argv[1], mode, &pins);
    if (r == R_NO_SUCH)
        reply_error(c, "no such session");
    else if (r == R_NOT_PINNED)
        reply_error(c, "not pinned");
    else if (mode == T_PIN)
        printf("ok pinned %s pins=%d\n", argv[1], pins);
    else if (mode == T_UNPIN)
        printf("ok unpinned %s pins=%d\n", argv[1], pins);
    else
        printf("ok touched %s\n", argv[1]);
}

static void do_close(Cache *c, int argc, char **argv)
{
    int left = 0;
    Result r;

    if (argc != 2) {
        reply_error(c, "usage: close ID");
        return;
    }
    if (!valid_id(argv[1])) {
        reply_error(c, "bad id");
        return;
    }
    r = cache_close(c, argv[1], &left);
    if (r == R_NO_SUCH)
        reply_error(c, "no such session");
    else if (r == R_PINNED)
        reply_error(c, "session pinned");
    else if (left == 0)
        printf("ok closed %s\n", argv[1]);
    else
        printf("ok released %s refs=%d\n", argv[1], left);
}

static void do_evict(Cache *c, int argc, char **argv)
{
    Result r;

    if (argc != 2) {
        reply_error(c, "usage: evict ID");
        return;
    }
    if (!valid_id(argv[1])) {
        reply_error(c, "bad id");
        return;
    }
    r = cache_evict(c, argv[1]);
    if (r == R_NO_SUCH)
        reply_error(c, "no such session");
    else if (r == R_PINNED)
        reply_error(c, "session pinned");
    else
        printf("ok evicted %s\n", argv[1]);
}

static void do_expire(Cache *c, int argc, char **argv)
{
    unsigned long age;
    size_t skipped, n;

    if (argc != 2) {
        reply_error(c, "usage: expire AGE");
        return;
    }
    if (!parse_number(argv[1], &age)) {
        reply_error(c, "bad number");
        return;
    }
    n = cache_expire(c, age, report_expired, NULL, &skipped);
    printf("ok expired %zu skipped=%zu\n", n, skipped);
}

void cmd_run_line(Cache *c, char *line)
{
    char *argv[MAX_ARGS + 1];
    int argc = 0;
    char *p = line;

    while (*p) {
        while (*p && isspace((unsigned char)*p))
            p++;
        if (!*p)
            break;
        if (argc == MAX_ARGS) {
            argc = MAX_ARGS + 1;
            break;
        }
        argv[argc++] = p;
        while (*p && !isspace((unsigned char)*p))
            p++;
        if (*p)
            *p++ = '\0';
    }
    if (argc == 0 || argv[0][0] == '#')
        return;

    cache_tick(c);
    if (argc > MAX_ARGS) {
        reply_error(c, "too many arguments");
        return;
    }
    if (strcmp(argv[0], "open") == 0)
        do_open(c, argc, argv);
    else if (strcmp(argv[0], "touch") == 0)
        do_touch(c, argc, argv);
    else if (strcmp(argv[0], "close") == 0)
        do_close(c, argc, argv);
    else if (strcmp(argv[0], "evict") == 0)
        do_evict(c, argc, argv);
    else if (strcmp(argv[0], "expire") == 0)
        do_expire(c, argc, argv);
    else if (strcmp(argv[0], "dump") == 0 && argc == 1)
        cache_dump(c, stdout);
    else if (strcmp(argv[0], "stats") == 0 && argc == 1)
        cache_stats(c, stdout);
    else if (strcmp(argv[0], "dump") == 0 || strcmp(argv[0], "stats") == 0)
        reply_error(c, "usage: dump | stats");
    else
        reply_error(c, "unknown command");
}
