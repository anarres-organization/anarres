/* Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29. */
#ifndef TILEKIT_H
#define TILEKIT_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define TK_MAX_IMAGES 8
#define TK_MAX_NAME 32
#define TK_MAX_CHANNELS 4
#define TK_MAX_FACTOR 65535u
#define TK_MAX_DIM ((uint64_t)1 << 24)    /* per-axis limit for declared sheets */
#define TK_MAX_BYTES ((size_t)1 << 24)    /* documented limit on any image */

#define TK_EXIT_SYNTAX 1
#define TK_EXIT_SEMANTIC 2
#define TK_EXIT_TOO_LARGE 3

typedef struct {
    char name[TK_MAX_NAME];
    unsigned int w, h, c;       /* width, height, channels */
    unsigned int tw, th;        /* tile size, 0 when the sheet declares none */
    unsigned char *pix;         /* w*h*c bytes, row-major, channels interleaved */
    size_t filled;              /* bytes decoded so far while loading */
    int used;
} Image;

typedef struct {
    Image imgs[TK_MAX_IMAGES];
    Image *loading;             /* image currently receiving rle data */
} Store;

/* util.c */
void tk_fail(int code, const char *msg);
int tk_parse_u64(const char *s, uint64_t *out);
uint64_t tk_need_u64(const char *s);
int tk_valid_name(const char *s);
int tk_split(char *line, char **tok, int max);

/* store.c */
Store *store_global(void);
Image *store_find(Store *st, const char *name);
Image *store_lookup(Store *st, const char *name);
Image *store_slot(Store *st, const char *name);
void store_install(Store *st, const char *name, unsigned char *buf,
                   unsigned int w, unsigned int h, unsigned int c);
void store_drop(Store *st, const char *name);
void store_release_all(void);

/* rle.c */
void rle_feed(Image *im, const char *text);

/* image.c */
void image_begin(Store *st, const char *name, uint64_t w, uint64_t h,
                 uint64_t c, uint64_t tw, uint64_t th);
void image_end(Store *st);
uint32_t image_checksum(const Image *im);
void image_report(const char *verb, const Image *im);
void image_info(const Image *im);
void op_crop(Store *st, const char *dst, const char *src,
             uint64_t x, uint64_t y, uint64_t w, uint64_t h);
void op_tile(Store *st, const char *dst, const char *src, uint64_t index);

/* ops.c */
void op_scale(Store *st, const char *dst, const char *src,
              uint64_t fx, uint64_t fy);
void op_concat(Store *st, const char *dst, const char *a, const char *b,
               int horizontal);

#endif
