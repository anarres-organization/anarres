# Task VSC-FX-05: stockdesk, names are mishandled

You have been handed a small Python 3.12 command-line program, `stockdesk`
(standard library only, sqlite3 in memory), in `src/`. Read `src/README.md`
first: it documents the input format, error handling, the CSV export rule and
the internal consistency check.

## The problem report

Several statements in the program are put together by string formatting
instead of bound parameters, and one export builds its CSV without escaping.
As a result, items whose names (or categories) contain quotes, semicolons,
commas or `%` / `_` characters are stored, searched or exported incorrectly,
and some runs end in `ERROR db:` lines or the program's own `INVARIANT:`
failure. Names must be handled as plain data everywhere, exactly as the README
documents. There may be more than one place with this problem; find the root
cause(s) by reading the code, and fix them without changing the documented
behaviour for ordinary input (valid names with quotes, commas, semicolons etc.
must still be accepted and stored verbatim; no new rejections).

## Deliverables

Create an `out/` directory containing:

* `out/patch/`: the complete fixed copy of `src/` (same layout; it is built with
  `sh build.sh` and run as `python3 main.py < NAME.in`).
* `out/tests/`: your own regression tests as pairs `NAME.in` / `NAME.out`, where
  `NAME.out` is the exact standard output the CORRECT program prints for
  `NAME.in`. Tests should show that the problem is fixed and that ordinary
  behaviour is kept. Keep them to plain, ordinary data.
* `out/REPORT.md`: a short write-up of the root cause and your fix.

## How a run is judged

A run is executed as `python3 main.py` from your build directory, with the
`.in` file on standard input, in a fresh empty working directory, with a 10
second limit. It FAILS if any of these holds: the exit code is not 0, standard
error contains `INVARIANT:` (the exit code 86 check) or a traceback, it times
out, or standard output differs from the expected `.out` byte for byte.

The examples in `smoke/` show the I/O format on ordinary input; your patched
build must keep passing them. Your work is checked with hidden tests of the
documented behaviour, your tests are also run against the original program and
against variants of the program that bring back parts of the problem, so
cover every place you find.

Time cap: 45 minutes.
