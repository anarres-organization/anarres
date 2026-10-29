/* Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29. */
/* logpack.h - shared types and prototypes for the logpack archive tool. */
#ifndef LOGPACK_H
#define LOGPACK_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define LP_MAGIC        "LPK1"
#define LP_MAGIC_LEN    4
#define LP_HEADER_SIZE  8      /* magic(4) version(1) flags(1) count(2) */
#define LP_VERSION      1
#define LP_PREFIX_SIZE  2      /* u16 body length in front of every record */
#define LP_MIN_BODY     6      /* ts(4) level(1) nfields(1) */
#define LP_FIELD_HDR    3      /* id(1) len(2) */
#define LP_MAX_FIELDS   16
#define LP_MAX_LEVEL    4
#define LP_FIELD_SHOW   32     /* bytes of a field value shown by extract */
#define LP_LIST_MSG_SHOW 60    /* bytes of a message shown by list */

#define LP_EXIT_OK      0
#define LP_EXIT_USAGE   1      /* bad command line, bad hex, no such record */
#define LP_EXIT_ARCHIVE 2      /* malformed archive */

typedef enum {
    LP_OK = 0,
    LP_E_TRUNCATED,
    LP_E_MAGIC,
    LP_E_VERSION,
    LP_E_RECORD
} lp_status;

typedef struct {
    uint8_t id;
    size_t len;
    const uint8_t *data;       /* points into the archive buffer */
} lp_field;

typedef struct {
    uint32_t ts;
    uint8_t level;
    unsigned nfields;
    lp_field fields[LP_MAX_FIELDS];
    const uint8_t *msg;        /* points into the archive buffer */
    size_t msg_len;
    size_t body_len;
} lp_record;

typedef struct {
    size_t body_off;           /* offset of the record body in the buffer */
    size_t body_len;           /* declared body length */
} lp_index_entry;

typedef struct {
    const uint8_t *buf;
    size_t size;
    unsigned count;
    size_t end;                /* offset just past the last record */
    lp_index_entry *index;     /* count entries */
} lp_archive;

/* hexin.c */
char *lp_read_all(FILE *in, size_t *n);
int lp_hex_decode(const char *text, size_t n, uint8_t **out, size_t *outlen);

/* archive.c */
const char *lp_status_message(lp_status st);
lp_status lp_record_parse(const uint8_t *body, size_t body_len, lp_record *out);
lp_status lp_archive_open(lp_archive *a, const uint8_t *buf, size_t size);
lp_status lp_archive_get(const lp_archive *a, unsigned i, lp_record *out);
void lp_archive_close(lp_archive *a);

/* report.c */
extern const char *const lp_level_names[LP_MAX_LEVEL + 1];
void lp_print_escaped(FILE *f, const uint8_t *s, size_t len, size_t max);
int lp_report_list(const lp_archive *a);
int lp_report_extract(const lp_archive *a, unsigned index);
int lp_report_stats(const lp_archive *a);

#endif
