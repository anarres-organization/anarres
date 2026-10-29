/* Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29. */
/* main.c - logpack command line driver.
 *
 * Input (stdin, or the file named by the only argument):
 *   line 1      the command: "list", "stats" or "extract <index>"
 *   remaining   the archive, hex encoded (whitespace ignored)
 * Every error is reported as one line "error: <reason>" on standard output.
 */
#include <ctype.h>
#include <stdlib.h>
#include <string.h>
#include "logpack.h"

typedef enum { CMD_LIST, CMD_STATS, CMD_EXTRACT } cmd_kind;

static int fail(int code, const char *msg)
{
    printf("error: %s\n", msg);
    return code;
}

/* Parse the command line (not NUL terminated, len bytes). */
static int parse_command(const char *line, size_t len, cmd_kind *kind,
                         unsigned *index)
{
    char tmp[64];
    char *arg;
    size_t i;

    while (len > 0 && isspace((unsigned char)line[len - 1]))
        len--;
    if (len == 0 || len >= sizeof tmp)
        return -1;
    memcpy(tmp, line, len);
    tmp[len] = '\0';

    if (strcmp(tmp, "list") == 0) { *kind = CMD_LIST; return 0; }
    if (strcmp(tmp, "stats") == 0) { *kind = CMD_STATS; return 0; }
    if (strncmp(tmp, "extract ", 8) == 0) {
        unsigned long v = 0;
        arg = tmp + 8;
        while (*arg == ' ')
            arg++;
        if (*arg == '\0')
            return -1;
        for (i = 0; arg[i] != '\0'; i++) {
            if (!isdigit((unsigned char)arg[i]))
                return -1;
            v = v * 10 + (unsigned long)(arg[i] - '0');
            if (v > 1000000UL)
                v = 1000000UL;   /* clamp: anything this large is out of range */
        }
        *kind = CMD_EXTRACT;
        *index = (unsigned)v;
        return 0;
    }
    return -1;
}

int main(int argc, char **argv)
{
    FILE *in = stdin;
    char *text, *nl;
    size_t n, cmd_len;
    uint8_t *bytes = NULL;
    size_t nbytes = 0;
    cmd_kind kind = CMD_LIST;
    unsigned index = 0;
    lp_archive arc;
    lp_status st;
    int rc;

    if (argc > 2)
        return fail(LP_EXIT_USAGE, "usage: logpack [file]");
    if (argc == 2) {
        in = fopen(argv[1], "r");
        if (in == NULL)
            return fail(LP_EXIT_USAGE, "cannot open input");
    }
    text = lp_read_all(in, &n);
    if (in != stdin)
        fclose(in);
    if (text == NULL)
        return fail(LP_EXIT_USAGE, "cannot read input");

    nl = memchr(text, '\n', n);
    cmd_len = nl ? (size_t)(nl - text) : n;
    if (parse_command(text, cmd_len, &kind, &index) != 0) {
        free(text);
        return fail(LP_EXIT_USAGE, "usage: list | stats | extract <index>");
    }
    if (nl == NULL) {
        n = 0;
    } else {
        n -= (size_t)(nl - text) + 1;
        nl++;
    }
    if (lp_hex_decode(nl ? nl : text, n, &bytes, &nbytes) != 0) {
        free(text);
        return fail(LP_EXIT_USAGE, "invalid hex input");
    }
    free(text);

    st = lp_archive_open(&arc, bytes, nbytes);
    if (st != LP_OK) {
        free(bytes);
        return fail(LP_EXIT_ARCHIVE, lp_status_message(st));
    }
    switch (kind) {
    case CMD_LIST:    rc = lp_report_list(&arc); break;
    case CMD_STATS:   rc = lp_report_stats(&arc); break;
    default:          rc = lp_report_extract(&arc, index); break;
    }
    lp_archive_close(&arc);
    free(bytes);
    return rc;
}
