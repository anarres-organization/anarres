/* Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29. */
/* Image block loading, checksum/report output, crop and tile extraction. */
#include "tilekit.h"

#include <stdlib.h>
#include <string.h>

/* Starts an "image" block: validates the declaration and allocates the pixel buffer. */
void image_begin(Store *st, const char *name, uint64_t w, uint64_t h,
                 uint64_t c, uint64_t tw, uint64_t th)
{
    Image *im;
    unsigned int nbytes;

    if (w < 1 || w > TK_MAX_DIM || h < 1 || h > TK_MAX_DIM ||
        c < 1 || c > TK_MAX_CHANNELS)
        tk_fail(TK_EXIT_SEMANTIC, "bad dimensions");
    if (tw != 0 || th != 0) {
        if (tw < 1 || th < 1 || tw > w || th > h)
            tk_fail(TK_EXIT_SEMANTIC, "bad tile size");
    }

    nbytes = (unsigned int)w * (unsigned int)h * (unsigned int)c;

    im = store_slot(st, name);
    im->w = (unsigned int)w;
    im->h = (unsigned int)h;
    im->c = (unsigned int)c;
    im->tw = (unsigned int)tw;
    im->th = (unsigned int)th;
    im->pix = malloc(nbytes ? nbytes : 1);
    if (!im->pix)
        tk_fail(TK_EXIT_SEMANTIC, "out of memory");
    st->loading = im;
}

/* Finishes the block opened by image_begin once all rle data is in. */
void image_end(Store *st)
{
    Image *im = st->loading;

    if ((size_t)im->w * im->h * im->c != im->filled)
        tk_fail(TK_EXIT_SEMANTIC, "pixel data length mismatch");
    st->loading = NULL;
    image_report("loaded", im);
}

/* 32-bit FNV-1a over the pixel bytes. */
uint32_t image_checksum(const Image *im)
{
    size_t n = (size_t)im->w * im->h * im->c;
    size_t i;
    uint32_t h = 2166136261u;

    for (i = 0; i < n; i++) {
        h ^= im->pix[i];
        h *= 16777619u;
    }
    return h;
}

void image_report(const char *verb, const Image *im)
{
    printf("%s %s %ux%ux%u fnv=%08x\n", verb, im->name, im->w, im->h, im->c,
           (unsigned int)image_checksum(im));
}

void image_info(const Image *im)
{
    size_t n = (size_t)im->w * im->h * im->c;

    printf("info %s %ux%ux%u bytes=%zu ", im->name, im->w, im->h, im->c, n);
    if (im->tw)
        printf("tile=%ux%u ", im->tw, im->th);
    else
        printf("tile=none ");
    printf("fnv=%08x\n", (unsigned int)image_checksum(im));
}

void op_crop(Store *st, const char *dst, const char *srcname,
             uint64_t x, uint64_t y, uint64_t w, uint64_t h)
{
    Image *src = store_lookup(st, srcname);
    unsigned char *buf;
    size_t row, nbytes, r;

    if (w < 1 || h < 1 || x > src->w || y > src->h ||
        w > src->w - x || h > src->h - y)
        tk_fail(TK_EXIT_SEMANTIC, "crop out of range");

    nbytes = (size_t)w * h * src->c;
    buf = malloc(nbytes);
    if (!buf)
        tk_fail(TK_EXIT_SEMANTIC, "out of memory");
    row = (size_t)w * src->c;
    for (r = 0; r < h; r++) {
        const unsigned char *from = src->pix + (((size_t)(y + r) * src->w) + x) * src->c;

        memcpy(buf + r * row, from, row);
    }
    store_install(st, dst, buf, (unsigned int)w, (unsigned int)h, src->c);
    image_report("crop", store_lookup(st, dst));
}

/* Extracts tile number index (row-major over the tile grid) from a sheet. */
void op_tile(Store *st, const char *dst, const char *srcname, uint64_t index)
{
    Image *src = store_lookup(st, srcname);
    uint64_t cols, rows, tx, ty;

    if (src->tw == 0)
        tk_fail(TK_EXIT_SEMANTIC, "no tile size");
    if (src->w % src->tw != 0 || src->h % src->th != 0)
        tk_fail(TK_EXIT_SEMANTIC, "sheet not divisible by tile size");
    cols = src->w / src->tw;
    rows = src->h / src->th;
    if (index >= cols * rows)
        tk_fail(TK_EXIT_SEMANTIC, "tile index out of range");
    tx = index % cols;
    ty = index / cols;

    {
        unsigned int tw = src->tw, th = src->th;
        unsigned char *buf;
        size_t row = (size_t)tw * src->c, r;

        buf = malloc(row * th);
        if (!buf)
            tk_fail(TK_EXIT_SEMANTIC, "out of memory");
        for (r = 0; r < th; r++) {
            const unsigned char *from =
                src->pix + (((size_t)(ty * th + r) * src->w) + tx * tw) * src->c;

            memcpy(buf + r * row, from, row);
        }
        store_install(st, dst, buf, tw, th, src->c);
    }
    image_report("tile", store_lookup(st, dst));
}
