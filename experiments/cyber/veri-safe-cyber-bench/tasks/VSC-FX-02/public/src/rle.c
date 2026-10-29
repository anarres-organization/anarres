/* Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29. */
/* Run-length decoder for the "rle" lines of an image block.
 * Tokens are either "V" (one byte of value V) or "N*V" (N bytes of value V);
 * V is a decimal 0..255. */
#include "tilekit.h"

#include <string.h>

void rle_feed(Image *im, const char *text)
{
    size_t total = (size_t)im->w * im->h * im->c;   /* declared pixel bytes */
    const char *p = text;

    for (;;) {
        char tok[48];
        size_t n = 0;
        uint64_t count = 1, value;
        char *star;

        while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n')
            p++;
        if (*p == '\0')
            break;
        while (*p && *p != ' ' && *p != '\t' && *p != '\r' && *p != '\n') {
            if (n + 1 >= sizeof tok)
                tk_fail(TK_EXIT_SYNTAX, "syntax");
            tok[n++] = *p++;
        }
        tok[n] = '\0';

        star = strchr(tok, '*');
        if (star) {
            *star = '\0';
            if (!tk_parse_u64(tok, &count) || !tk_parse_u64(star + 1, &value))
                tk_fail(TK_EXIT_SYNTAX, "syntax");
        } else if (!tk_parse_u64(tok, &value)) {
            tk_fail(TK_EXIT_SYNTAX, "syntax");
        }
        if (count == 0 || value > 255)
            tk_fail(TK_EXIT_SYNTAX, "syntax");
        if (count > total - im->filled)
            tk_fail(TK_EXIT_SEMANTIC, "pixel data overflow");

        memset(im->pix + im->filled, (int)value, (size_t)count);
        im->filled += (size_t)count;
    }
}
