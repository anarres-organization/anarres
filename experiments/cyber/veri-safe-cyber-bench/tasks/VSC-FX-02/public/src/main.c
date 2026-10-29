/* Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29. */
/* tilekit: reads a script from stdin, one command per line.  See README.md. */
#include "tilekit.h"

#include <stdlib.h>
#include <string.h>

#define MAX_TOKENS 10

static void need(int n, int want)
{
    if (n != want)
        tk_fail(TK_EXIT_SYNTAX, "syntax");
}

static void need_name(const char *s)
{
    if (!tk_valid_name(s))
        tk_fail(TK_EXIT_SYNTAX, "syntax");
}

static void cmd_image(Store *st, char **tok, int n)
{
    uint64_t tw = 0, th = 0;

    if (n != 5 && n != 8)
        tk_fail(TK_EXIT_SYNTAX, "syntax");
    need_name(tok[1]);
    if (n == 8) {
        if (strcmp(tok[5], "tile") != 0)
            tk_fail(TK_EXIT_SYNTAX, "syntax");
        tw = tk_need_u64(tok[6]);
        th = tk_need_u64(tok[7]);
        if (tw == 0 && th == 0)
            tk_fail(TK_EXIT_SYNTAX, "syntax");
    }
    image_begin(st, tok[1], tk_need_u64(tok[2]), tk_need_u64(tok[3]),
                tk_need_u64(tok[4]), tw, th);
}

static void run_line(Store *st, char *line)
{
    char *hash = strchr(line, '#');
    char *tok[MAX_TOKENS];
    char *p;
    int n;

    if (hash)
        *hash = '\0';
    p = line;
    while (*p == ' ' || *p == '\t')
        p++;

    if (st->loading && strncmp(p, "rle", 3) == 0 &&
        (p[3] == ' ' || p[3] == '\t' || p[3] == '\0' || p[3] == '\n' || p[3] == '\r')) {
        rle_feed(st->loading, p + 3);
        return;
    }

    n = tk_split(p, tok, MAX_TOKENS);
    if (n < 0)
        tk_fail(TK_EXIT_SYNTAX, "syntax");
    if (n == 0)
        return;

    if (st->loading) {
        if (strcmp(tok[0], "end") != 0)
            tk_fail(TK_EXIT_SYNTAX, "unterminated image");
        need(n, 1);
        image_end(st);
    } else if (strcmp(tok[0], "image") == 0) {
        cmd_image(st, tok, n);
    } else if (strcmp(tok[0], "crop") == 0) {
        need(n, 7);
        need_name(tok[1]);
        op_crop(st, tok[1], tok[2], tk_need_u64(tok[3]), tk_need_u64(tok[4]),
                tk_need_u64(tok[5]), tk_need_u64(tok[6]));
    } else if (strcmp(tok[0], "tile") == 0) {
        need(n, 4);
        need_name(tok[1]);
        op_tile(st, tok[1], tok[2], tk_need_u64(tok[3]));
    } else if (strcmp(tok[0], "scale") == 0) {
        need(n, 5);
        need_name(tok[1]);
        op_scale(st, tok[1], tok[2], tk_need_u64(tok[3]), tk_need_u64(tok[4]));
    } else if (strcmp(tok[0], "concat") == 0) {
        int horizontal = 0;

        need(n, 5);
        need_name(tok[1]);
        if (strcmp(tok[4], "h") == 0)
            horizontal = 1;
        else if (strcmp(tok[4], "v") == 0)
            horizontal = 0;
        else
            tk_fail(TK_EXIT_SYNTAX, "syntax");
        op_concat(st, tok[1], tok[2], tok[3], horizontal);
    } else if (strcmp(tok[0], "info") == 0) {
        need(n, 2);
        image_info(store_lookup(st, tok[1]));
    } else if (strcmp(tok[0], "drop") == 0) {
        need(n, 2);
        store_drop(st, tok[1]);
        printf("dropped %s\n", tok[1]);
    } else {
        tk_fail(TK_EXIT_SYNTAX, "syntax");
    }
}

int main(void)
{
    Store *st = store_global();
    char *line = NULL;
    size_t cap = 0;

    atexit(store_release_all);
    while (getline(&line, &cap, stdin) != -1)
        run_line(st, line);
    free(line);
    if (st->loading)
        tk_fail(TK_EXIT_SYNTAX, "unterminated image");
    return 0;
}
