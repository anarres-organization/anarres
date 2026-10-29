/* Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29. */
/* Error reporting, strict number parsing and line splitting. */
#include "tilekit.h"

#include <ctype.h>
#include <stdlib.h>
#include <string.h>

void tk_fail(int code, const char *msg)
{
    printf("error: %s\n", msg);
    fflush(stdout);
    exit(code);
}

/* Strict decimal parse: digits only, no sign, no overflow of uint64_t. */
int tk_parse_u64(const char *s, uint64_t *out)
{
    uint64_t v = 0;

    if (*s == '\0')
        return 0;
    for (; *s; s++) {
        unsigned int d;

        if (*s < '0' || *s > '9')
            return 0;
        d = (unsigned int)(*s - '0');
        if (v > (UINT64_MAX - d) / 10)
            return 0;
        v = v * 10 + d;
    }
    *out = v;
    return 1;
}

uint64_t tk_need_u64(const char *s)
{
    uint64_t v;

    if (!tk_parse_u64(s, &v))
        tk_fail(TK_EXIT_SYNTAX, "syntax");
    return v;
}

int tk_valid_name(const char *s)
{
    size_t n = strlen(s);

    if (n == 0 || n >= TK_MAX_NAME)
        return 0;
    for (; *s; s++) {
        if (!isalnum((unsigned char)*s) && *s != '_')
            return 0;
    }
    return 1;
}

/* Split on blanks in place. Returns the token count, or -1 if more than max. */
int tk_split(char *line, char **tok, int max)
{
    int n = 0;
    char *p = line;

    for (;;) {
        while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n')
            p++;
        if (*p == '\0')
            break;
        if (n == max)
            return -1;
        tok[n++] = p;
        while (*p && *p != ' ' && *p != '\t' && *p != '\r' && *p != '\n')
            p++;
        if (*p)
            *p++ = '\0';
    }
    return n;
}
