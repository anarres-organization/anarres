/* Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29. */
/* hexin.c - read the input text and decode hex into a byte buffer. */
#include <ctype.h>
#include <stdlib.h>
#include <string.h>
#include "logpack.h"

char *lp_read_all(FILE *in, size_t *n)
{
    size_t cap = 4096, len = 0, got;
    char *buf = malloc(cap);

    if (buf == NULL)
        return NULL;
    while ((got = fread(buf + len, 1, cap - len, in)) > 0) {
        len += got;
        if (len == cap) {
            char *bigger = realloc(buf, cap * 2);
            if (bigger == NULL) {
                free(buf);
                return NULL;
            }
            buf = bigger;
            cap *= 2;
        }
    }
    *n = len;
    return buf;
}

static int hex_val(int c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

/* Decode hex digits (whitespace between digits is ignored).  Returns 0 on
 * success, -1 on a stray character or an odd number of digits.  The output
 * buffer is allocated with exactly the decoded size. */
int lp_hex_decode(const char *text, size_t n, uint8_t **out, size_t *outlen)
{
    size_t i, digits = 0, o = 0;
    int hi = -1;
    uint8_t *buf;

    for (i = 0; i < n; i++) {
        unsigned char c = (unsigned char)text[i];
        if (isspace(c))
            continue;
        if (hex_val(c) < 0)
            return -1;
        digits++;
    }
    if (digits % 2 != 0)
        return -1;
    buf = malloc(digits / 2 ? digits / 2 : 1);
    if (buf == NULL)
        return -1;
    for (i = 0; i < n; i++) {
        unsigned char c = (unsigned char)text[i];
        int v;
        if (isspace(c))
            continue;
        v = hex_val(c);
        if (hi < 0) {
            hi = v;
        } else {
            buf[o++] = (uint8_t)((hi << 4) | v);
            hi = -1;
        }
    }
    *out = buf;
    *outlen = o;
    return 0;
}
