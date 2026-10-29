# Author notes: VSC-FX-01 (logpack)

Story: toy log-record archive tool. Input is a command line plus hex text.
Container: 8-byte header (magic, version, flags, u16 record count), records
with a u16 body length prefix, each body = ts, level, nfields, nested fields
(id, u16 length, data) and a trailing message that is the rest of the body.

## The defect (K = 3 variants, all in `archive.c`)

Declared lengths are not all validated against the bytes actually present.
The original (public/src) has all three; gold has none; each mutant brings
back exactly one.

1. M1_count_vs_size (`lp_archive_open`, loop head): the record count in the
   header can exceed the records present; the loop reads the 2-byte length
   prefix of the next record without checking that two bytes remain.
   Gold: `if (size - pos < LP_PREFIX_SIZE) -> truncated`.
2. M2_record_len (`lp_archive_open`): the record body check is written as
   `pos + body_len > size` where `pos` is the offset of the length prefix, so
   it forgets the 2 prefix bytes and a body that runs 1 or 2 bytes past the
   end is accepted. Gold: `body_len > size - body_off`.
3. M3_field_len (`lp_record_parse`): a field length is compared with the whole
   body length instead of with what is left of the body after the field
   header. A field longer than the rest of the body but not longer than the
   body is accepted; the following message length then wraps around.
   Gold: `flen > body_len - pos - LP_FIELD_HDR`.

## Intended fix

Check each declared length against the remaining bytes of the thing that
contains it (archive for prefix and body, record body for field header and
field data), using subtraction on size_t values that are already known to be
in range (no `pos + len` additions that can be wrong or wrap).

## Traps

* Partial fix: the most visible variant is the record body check. A fixer who
  only corrects that line leaves the count/prefix read (M1) and the nested field
  length (M3). RC_edge separates real fixes (controls: naive partial fix scores
  3/11 on ref_edge).
* Over-aggressive fix: rejecting archives with trailing bytes (README: ignored),
  rejecting a field that ends exactly at the end of the body (empty message),
  using `>=` instead of `>`, rejecting count 0, or rejecting empty fields or
  messages. ref_tests contains valid cases for each of those.
* Check order is documented (file order, first problem wins), so a fix that
  validates the whole count up front can report the wrong error.
* Original already rejects very large lengths (record length 0xFFFF, field
  length larger than the whole body); those cases are in ref_tests, so a
  solver that only tests "huge lengths" will not see the failures.

## Test conventions

Tests are plain text: line 1 is the command, the rest is the hex archive.
Errors are printed on stdout (one `error: ...` line), so `.out` carries them.
The scorer also derives the exit status from the expected first line
(`error: usage|invalid hex|no such record` -> 1, other `error:` -> 2, else 0)
and treats any ASan/UBSan message on stderr as a failure.

## Rebuilding

`sh private/build_private.sh` regenerates public/src, mutants, controls, smoke
inputs and every .in/.out (expected output is produced by gold).
`python3 private/run_controls.py` regenerates `private/CONTROLS.md`.
