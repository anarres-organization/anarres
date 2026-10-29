/* Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29. */
/* report.c - text output for the list, extract and stats commands. */
#include <stdio.h>
#include <string.h>
#include "logpack.h"

const char *const lp_level_names[LP_MAX_LEVEL + 1] = {
    "DEBUG", "INFO", "WARN", "ERROR", "FATAL"
};

static const char *field_name(unsigned id)
{
    switch (id) {
    case 1: return "host";
    case 2: return "pid";
    case 3: return "tag";
    default: return NULL;
    }
}

/* Print s as a quoted string.  Backslash and double quote are escaped,
 * bytes outside 0x20..0x7e are written as \xNN.  At most max bytes are
 * shown (max == 0 means no limit); a "..." marker follows a cut value. */
void lp_print_escaped(FILE *f, const uint8_t *s, size_t len, size_t max)
{
    size_t i, n = len;

    if (max != 0 && n > max)
        n = max;
    fputc('"', f);
    for (i = 0; i < n; i++) {
        uint8_t c = s[i];
        if (c == '"' || c == '\\') {
            fputc('\\', f);
            fputc(c, f);
        } else if (c >= 0x20 && c < 0x7f) {
            fputc(c, f);
        } else {
            fprintf(f, "\\x%02x", c);
        }
    }
    fputc('"', f);
    if (n < len)
        fputs("...", f);
}

int lp_report_list(const lp_archive *a)
{
    unsigned i;

    for (i = 0; i < a->count; i++) {
        lp_record rec;
        if (lp_archive_get(a, i, &rec) != LP_OK)
            return LP_EXIT_ARCHIVE;
        printf("%u ts=%lu %s fields=%u msg=", i, (unsigned long)rec.ts,
               lp_level_names[rec.level], rec.nfields);
        lp_print_escaped(stdout, rec.msg, rec.msg_len, LP_LIST_MSG_SHOW);
        fputc('\n', stdout);
    }
    return LP_EXIT_OK;
}

int lp_report_extract(const lp_archive *a, unsigned index)
{
    lp_record rec;
    unsigned i;

    if (index >= a->count) {
        printf("error: no such record\n");
        return LP_EXIT_USAGE;
    }
    if (lp_archive_get(a, index, &rec) != LP_OK)
        return LP_EXIT_ARCHIVE;
    printf("record %u\n", index);
    printf("  time: %lu\n", (unsigned long)rec.ts);
    printf("  level: %s\n", lp_level_names[rec.level]);
    printf("  fields: %u\n", rec.nfields);
    for (i = 0; i < rec.nfields; i++) {
        const lp_field *f = &rec.fields[i];
        const char *name = field_name(f->id);
        if (name != NULL)
            printf("  field %u (%s) len=%zu: ", (unsigned)f->id, name, f->len);
        else
            printf("  field %u len=%zu: ", (unsigned)f->id, f->len);
        lp_print_escaped(stdout, f->data, f->len, LP_FIELD_SHOW);
        fputc('\n', stdout);
    }
    printf("  message (%zu bytes): ", rec.msg_len);
    lp_print_escaped(stdout, rec.msg, rec.msg_len, 0);
    fputc('\n', stdout);
    return LP_EXIT_OK;
}

int lp_report_stats(const lp_archive *a)
{
    unsigned levels[LP_MAX_LEVEL + 1];
    unsigned long min_ts = 0, max_ts = 0;
    unsigned long fields_total = 0, msg_bytes = 0, largest = 0;
    unsigned i;

    memset(levels, 0, sizeof levels);
    for (i = 0; i < a->count; i++) {
        lp_record rec;
        unsigned long ts;
        if (lp_archive_get(a, i, &rec) != LP_OK)
            return LP_EXIT_ARCHIVE;
        ts = rec.ts;
        if (i == 0 || ts < min_ts) min_ts = ts;
        if (i == 0 || ts > max_ts) max_ts = ts;
        levels[rec.level]++;
        fields_total += rec.nfields;
        msg_bytes += rec.msg_len;
        if (rec.body_len > largest) largest = rec.body_len;
    }
    printf("records: %u\n", a->count);
    printf("levels:");
    for (i = 0; i <= LP_MAX_LEVEL; i++)
        printf(" %s=%u", lp_level_names[i], levels[i]);
    fputc('\n', stdout);
    if (a->count > 0) {
        printf("min_ts: %lu\n", min_ts);
        printf("max_ts: %lu\n", max_ts);
        printf("span_seconds: %lu\n", max_ts - min_ts);
    } else {
        printf("min_ts: -\nmax_ts: -\nspan_seconds: -\n");
    }
    printf("fields_total: %lu\n", fields_total);
    printf("message_bytes: %lu\n", msg_bytes);
    printf("largest_record_body: %lu\n", largest);
    printf("archive_bytes: %zu\n", a->size);
    printf("trailing_bytes: %zu\n", a->size - a->end);
    return LP_EXIT_OK;
}
