# logpack

`logpack` is a small command line tool for a fictional log-record archive
format ("LPK1"). A support team keeps batches of application log records in
one binary container; `logpack` validates a container and prints a text
summary of it. This is toy, synthetic code used for maintenance exercises.

## Building and running

    sh build.sh          # produces ./logpack (AddressSanitizer + UBSan build)
    ./logpack < case.in  # or: ./logpack case.in

To keep test transcripts plain text, the tool reads text, not raw bytes:

* line 1 is the command: `list`, `stats` or `extract <index>`
* everything after line 1 is the archive, hex encoded; whitespace (spaces,
  tabs, CR, LF) between hex digits is ignored, upper and lower case are
  both accepted

Commands:

* `list` prints one line per record: `<index> ts=<ts> <LEVEL> fields=<n> msg=<text>`
  (message text is shown at most 60 bytes, a longer one is followed by `...`)
* `extract <index>` prints the full detail of one record (field values are
  shown at most 32 bytes, followed by `...` when cut)
* `stats` prints record counts per level, time range and size totals

Text is printed in double quotes. `\` and `"` are escaped with a backslash,
bytes outside 0x20..0x7e are printed as `\xNN`.

## Container format (all integers little endian)

    Archive  = Header Record{count} Trailer
    Header   = magic "LPK1" (4 bytes) | version u8 (must be 1)
               | flags u8 (reserved, ignored) | count u16
    Record   = body_len u16 | body (body_len bytes)
    body     = ts u32 | level u8 | nfields u8 | Field{nfields} | message
    Field    = id u8 | field_len u16 | data (field_len bytes)
    message  = all bytes of the body that follow the last field (may be empty)
    Trailer  = any bytes after the last record (ignored, may be empty)

Rules:

* The header is 8 bytes, and `count` is the number of records that follow.
  `count` may be 0.
* `level` is 0..4 (DEBUG, INFO, WARN, ERROR, FATAL).
* A record has at most 16 fields. A field may have `field_len` 0, and the
  message may be empty. A field may end exactly at the end of the body.
* A record body is at least 6 bytes (`ts`, `level`, `nfields`).
* A record is only valid if all of its declared lengths fit: the 2-byte
  `body_len` prefix and the body must lie inside the archive, and every
  field header (3 bytes) and field data must lie inside the body of the
  record that contains them. Lengths in the file are never trusted beyond
  the bytes that are actually present.

## Errors and exit codes

Every error is one line on standard output and a non-zero exit status. The
archive is validated completely before anything else is printed, so a
rejected archive produces only the error line.

| situation                                                      | output                                  | exit |
|----------------------------------------------------------------|-----------------------------------------|------|
| unknown command, missing or non-numeric extract index          | `error: usage: list \| stats \| extract <index>` | 1 |
| input text is not valid hex (stray character, odd digit count) | `error: invalid hex input`              | 1    |
| fewer than 8 bytes, or any declared length (record count, record length, field header or field length) runs past the bytes that are present | `error: truncated archive` | 2 |
| magic is not `LPK1`                                            | `error: bad magic`                      | 2    |
| version is not 1                                               | `error: unsupported version`            | 2    |
| record body shorter than 6 bytes, level above 4, more than 16 fields | `error: invalid record`           | 2    |
| `extract` index not smaller than the record count              | `error: no such record`                 | 1    |

Checks run in file order and the first problem found is the one reported:
header (length, magic, version), then record 0, record 1, ... For one record
the order is: length prefix, body fits, body at least 6 bytes, level, field
count, then the fields from first to last.

## Source layout

* `main.c` command line, input handling
* `hexin.c` reading input, hex decoding
* `archive.c` container validation, record decoding
* `report.c` the three commands' text output
* `logpack.h` shared types and constants
