/*
 * Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
 *
 * sesscache.h - types and API of the toy session cache.
 */
#ifndef SESSCACHE_H
#define SESSCACHE_H

#include <stddef.h>
#include <stdio.h>

#define ID_MAX        15      /* longest session id, in characters   */
#define CAPACITY      6       /* most sessions held at one time      */
#define HASH_BUCKETS  16
#define MAX_PAYLOAD   4096    /* largest single payload, in bytes    */
#define POOL_LIMIT    8192    /* total payload bytes the cache may hold */
#define DEFAULT_SIZE  16
typedef struct Entry {
    char id[ID_MAX + 1];
    unsigned char *payload;
    size_t size;
    int refs;                 /* open count: one per "open" of this id   */
    int pins;                 /* pin count: pinned sessions are protected */
    unsigned long last_tick;  /* logical time of the last open/touch     */
    struct Entry *hnext;      /* hash bucket chain                        */
    struct Entry *lru_prev;   /* towards the most recently used end       */
    struct Entry *lru_next;   /* towards the least recently used end      */
} Entry;
typedef struct Stats {
    unsigned long opened, reopened, closed, evicted, expired;
    unsigned long open_failed, pinned_skips, errors;
} Stats;
typedef struct Cache {
    Entry *buckets[HASH_BUCKETS];
    Entry *lru_head;          /* most recently used  */
    Entry *lru_tail;          /* least recently used */
    Entry *pinned[CAPACITY];  /* every entry with pins > 0 (the pin set) */
    int npinned;
    int count;                /* number of sessions in the cache */
    size_t pool_used;         /* payload bytes currently held    */
    unsigned long tick;       /* logical clock                   */
    Stats st;
} Cache;
typedef enum { R_OK, R_NO_SUCH, R_PINNED, R_FULL, R_FAILED, R_NOT_PINNED } Result;
typedef enum { T_PLAIN, T_PIN, T_UNPIN } TouchMode;
typedef struct OpenInfo {
    int reopened;
    int refs;
    char evicted[ID_MAX + 1]; /* id evicted to make room, "" if none */
} OpenInfo;
typedef void (*ExpireReport)(void *ctx, const char *id);
void   cache_init(Cache *c);
void   cache_destroy(Cache *c);
void   cache_tick(Cache *c);

Result cache_open(Cache *c, const char *id, size_t size, OpenInfo *info);
Result cache_touch(Cache *c, const char *id, TouchMode mode, int *pins);
Result cache_close(Cache *c, const char *id, int *refs_left);
Result cache_evict(Cache *c, const char *id);
size_t cache_expire(Cache *c, unsigned long age, ExpireReport report,
                    void *ctx, size_t *skipped);

void   cache_dump(const Cache *c, FILE *out);
void   cache_stats(const Cache *c, FILE *out);

void   cmd_run_line(Cache *c, char *line);

#endif
