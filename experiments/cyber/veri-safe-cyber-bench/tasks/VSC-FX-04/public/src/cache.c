/*
 * Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
 *
 * cache.c - session table (hash index), LRU list, pin set, payload pool.
 *
 * Lifetime rules used by this file:
 *   - an entry is reachable from three places: the hash index, the LRU list
 *     and (while pins > 0) the pin set;
 *   - payload bytes are charged against a fixed pool (POOL_LIMIT).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sesscache.h"

/* ---------- hash index ---------- */

static unsigned hash_id(const char *id)
{
    unsigned h = 5381u;
    while (*id)
        h = h * 33u + (unsigned char)*id++;
    return h % HASH_BUCKETS;
}

static Entry *hash_find(Cache *c, const char *id)
{
    Entry *e = c->buckets[hash_id(id)];
    while (e && strcmp(e->id, id) != 0)
        e = e->hnext;
    return e;
}

static void hash_insert(Cache *c, Entry *e)
{
    unsigned b = hash_id(e->id);
    e->hnext = c->buckets[b];
    c->buckets[b] = e;
}

static void hash_remove(Cache *c, Entry *e)
{
    Entry **pp = &c->buckets[hash_id(e->id)];
    while (*pp && *pp != e)
        pp = &(*pp)->hnext;
    if (*pp)
        *pp = e->hnext;
}

/* ---------- LRU list (head = most recently used) ---------- */

static void lru_push_front(Cache *c, Entry *e)
{
    e->lru_prev = NULL;
    e->lru_next = c->lru_head;
    if (c->lru_head)
        c->lru_head->lru_prev = e;
    else
        c->lru_tail = e;
    c->lru_head = e;
}

static void lru_unlink(Cache *c, Entry *e)
{
    if (e->lru_prev)
        e->lru_prev->lru_next = e->lru_next;
    else
        c->lru_head = e->lru_next;
    if (e->lru_next)
        e->lru_next->lru_prev = e->lru_prev;
    else
        c->lru_tail = e->lru_prev;
    e->lru_prev = NULL;
    e->lru_next = NULL;
}

static void lru_touch(Cache *c, Entry *e)
{
    lru_unlink(c, e);
    lru_push_front(c, e);
}

/* ---------- pin set ---------- */

static void pin_set_add(Cache *c, Entry *e)
{
    if (c->npinned < CAPACITY)
        c->pinned[c->npinned++] = e;
}

static void pin_set_remove(Cache *c, Entry *e)
{
    int i;
    for (i = 0; i < c->npinned; i++) {
        if (c->pinned[i] == e) {
            c->pinned[i] = c->pinned[--c->npinned];
            return;
        }
    }
}

/* ---------- payload pool ---------- */

/* Returns a filled payload buffer and charges the pool, or NULL when the
 * size is out of range or the pool budget would be exceeded. */
static unsigned char *payload_alloc(Cache *c, const char *id, size_t size)
{
    unsigned char *p;
    unsigned seed = 0;
    size_t i;

    if (size == 0 || size > MAX_PAYLOAD)
        return NULL;
    if (c->pool_used + size > POOL_LIMIT)
        return NULL;
    p = malloc(size);
    if (!p)
        return NULL;
    for (; *id; id++)
        seed = seed * 31u + (unsigned char)*id;
    for (i = 0; i < size; i++)
        p[i] = (unsigned char)(seed + i * 7u);
    c->pool_used += size;
    return p;
}

static void payload_free(Cache *c, unsigned char *p, size_t size)
{
    if (!p)
        return;
    c->pool_used -= size;
    free(p);
}

/* ---------- entry teardown ---------- */

static void entry_destroy(Cache *c, Entry *e)
{
    payload_free(c, e->payload, e->size);
    free(e);
}

/* Remove an entry from every structure that can reach it, then free it. */
static void entry_drop(Cache *c, Entry *e)
{
    hash_remove(c, e);
    lru_unlink(c, e);
    pin_set_remove(c, e);
    c->count--;
    entry_destroy(c, e);
}

/* Oldest entry that is not pinned, or NULL. */
static Entry *pick_victim(Cache *c)
{
    Entry *e;
    for (e = c->lru_tail; e; e = e->lru_prev)
        if (e->pins == 0)
            return e;
    return NULL;
}

/* ---------- public API ---------- */

void cache_init(Cache *c)
{
    memset(c, 0, sizeof *c);
}

void cache_destroy(Cache *c)
{
    while (c->lru_head)
        entry_drop(c, c->lru_head);
}

void cache_tick(Cache *c)
{
    c->tick++;
}

Result cache_open(Cache *c, const char *id, size_t size, OpenInfo *info)
{
    Entry *e;

    info->reopened = 0;
    info->refs = 0;
    info->evicted[0] = '\0';

    e = hash_find(c, id);
    if (e) {
        e->refs++;
        e->last_tick = c->tick;
        lru_touch(c, e);
        c->st.reopened++;
        info->reopened = 1;
        info->refs = e->refs;
        return R_OK;
    }

    if (c->count >= CAPACITY) {
        Entry *victim = pick_victim(c);
        if (!victim)
            return R_FULL;
        snprintf(info->evicted, sizeof info->evicted, "%s", victim->id);
        entry_drop(c, victim);
        c->st.evicted++;
    }
    e = calloc(1, sizeof *e);
    if (!e) {
        c->st.open_failed++;
        return R_FAILED;
    }
    snprintf(e->id, sizeof e->id, "%s", id);
    e->size = size;
    e->refs = 1;
    e->last_tick = c->tick;
    hash_insert(c, e);
    lru_push_front(c, e);
    c->count++;
    e->payload = payload_alloc(c, id, size);
    if (!e->payload) {
        /* no payload buffer: give the entry back */
        free(e);
        c->st.open_failed++;
        return R_FAILED;
    }
    c->st.opened++;
    info->refs = 1;
    return R_OK;
}

Result cache_touch(Cache *c, const char *id, TouchMode mode, int *pins)
{
    Entry *e = hash_find(c, id);

    if (!e)
        return R_NO_SUCH;
    if (mode == T_UNPIN && e->pins == 0)
        return R_NOT_PINNED;
    if (mode == T_PIN) {
        if (e->pins++ == 0)
            pin_set_add(c, e);
    } else if (mode == T_UNPIN) {
        if (--e->pins == 0)
            pin_set_remove(c, e);
    }
    e->last_tick = c->tick;
    lru_touch(c, e);
    *pins = e->pins;
    return R_OK;
}

Result cache_close(Cache *c, const char *id, int *refs_left)
{
    Entry *e = hash_find(c, id);

    if (!e)
        return R_NO_SUCH;
    if (e->refs == 1 && e->pins > 0)
        return R_PINNED;
    e->refs--;
    *refs_left = e->refs;
    if (e->refs == 0) {
        entry_drop(c, e);
        c->st.closed++;
    }
    return R_OK;
}

Result cache_evict(Cache *c, const char *id)
{
    Entry *e = hash_find(c, id);

    if (!e)
        return R_NO_SUCH;
    if (e->pins > 0)
        return R_PINNED;
    lru_unlink(c, e);
    c->count--;
    entry_destroy(c, e);
    c->st.evicted++;
    return R_OK;
}

size_t cache_expire(Cache *c, unsigned long age, ExpireReport report,
                    void *ctx, size_t *skipped)
{
    Entry *e, *prev;
    size_t n = 0;

    *skipped = 0;
    for (e = c->lru_tail; e; e = prev) {
        prev = e->lru_prev;
        if (c->tick - e->last_tick < age)
            continue;
        report(ctx, e->id);
        hash_remove(c, e);
        lru_unlink(c, e);
        c->count--;
        entry_destroy(c, e);
        c->st.expired++;
        n++;
    }
    return n;
}

/* ---------- reporting ---------- */

static unsigned payload_sum(const Entry *e)
{
    unsigned sum = 0;
    size_t i;
    for (i = 0; i < e->size; i++)
        sum += e->payload[i];
    return sum % 65521u;
}

void cache_dump(const Cache *c, FILE *out)
{
    const Entry *e;

    fprintf(out, "dump: %d sessions\n", c->count);
    for (e = c->lru_head; e; e = e->lru_next)
        fprintf(out, "  %s refs=%d pins=%d size=%zu sum=%u idle=%lu\n",
                e->id, e->refs, e->pins, e->size, payload_sum(e),
                c->tick - e->last_tick);
}

void cache_stats(const Cache *c, FILE *out)
{
    size_t pinned_bytes = 0;
    int i;

    for (i = 0; i < c->npinned; i++)
        pinned_bytes += c->pinned[i]->size;
    fprintf(out, "stats: sessions=%d pinned=%d pinned_bytes=%zu pool=%zu/%d\n",
            c->count, c->npinned, pinned_bytes, c->pool_used, POOL_LIMIT);
    fprintf(out, "stats: opened=%lu reopened=%lu closed=%lu evicted=%lu "
            "expired=%lu open_failed=%lu pinned_skips=%lu errors=%lu\n",
            c->st.opened, c->st.reopened, c->st.closed, c->st.evicted,
            c->st.expired, c->st.open_failed, c->st.pinned_skips,
            c->st.errors);
}
