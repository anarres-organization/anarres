/* Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29. */
/* Fixed-size table of named images. */
#include "tilekit.h"

#include <stdlib.h>
#include <string.h>

static Store g_store;

Store *store_global(void)
{
    return &g_store;
}

static void image_clear(Image *im)
{
    free(im->pix);
    memset(im, 0, sizeof *im);
}

Image *store_find(Store *st, const char *name)
{
    int i;

    for (i = 0; i < TK_MAX_IMAGES; i++) {
        if (st->imgs[i].used && strcmp(st->imgs[i].name, name) == 0)
            return &st->imgs[i];
    }
    return NULL;
}

Image *store_lookup(Store *st, const char *name)
{
    Image *im = store_find(st, name);

    if (!im)
        tk_fail(TK_EXIT_SEMANTIC, "unknown image");
    return im;
}

/* Returns an empty slot carrying the name; an existing image of that name is replaced. */
Image *store_slot(Store *st, const char *name)
{
    Image *im = store_find(st, name);
    int i;

    if (!im) {
        for (i = 0; i < TK_MAX_IMAGES; i++) {
            if (!st->imgs[i].used) {
                im = &st->imgs[i];
                break;
            }
        }
        if (!im)
            tk_fail(TK_EXIT_SEMANTIC, "too many images");
    }
    image_clear(im);
    im->used = 1;
    strncpy(im->name, name, TK_MAX_NAME - 1);
    return im;
}

/* Takes ownership of buf (w*h*c bytes) as the new image called name. */
void store_install(Store *st, const char *name, unsigned char *buf,
                   unsigned int w, unsigned int h, unsigned int c)
{
    Image *im = store_find(st, name);
    int i;

    if (!im) {
        for (i = 0; i < TK_MAX_IMAGES; i++) {
            if (!st->imgs[i].used)
                break;
        }
        if (i == TK_MAX_IMAGES) {
            free(buf);
            tk_fail(TK_EXIT_SEMANTIC, "too many images");
        }
    }
    im = store_slot(st, name);
    im->w = w;
    im->h = h;
    im->c = c;
    im->pix = buf;
    im->filled = (size_t)w * h * c;
}

void store_drop(Store *st, const char *name)
{
    image_clear(store_lookup(st, name));
}

void store_release_all(void)
{
    int i;

    for (i = 0; i < TK_MAX_IMAGES; i++)
        image_clear(&g_store.imgs[i]);
}
