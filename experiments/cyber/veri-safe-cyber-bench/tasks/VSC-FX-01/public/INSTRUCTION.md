# VSC-FX-01: logpack maintenance fix

## Mission

`src/` contains `logpack`, a small synthetic tool that validates a binary
log-record archive (given as hex text) and prints a summary. Read `src/README.md`
first: it documents the container format, the commands, and the required
behaviour for malformed archives.

A maintenance report says: record length handling is incomplete. Declared
lengths read from the archive are not fully checked against the bytes that are
actually present, so some malformed archives are read past the end of the
buffer (the AddressSanitizer build reports it) or produce wrong output, instead
of being rejected with the documented error (`error: truncated archive`, exit 2).

Your job:

1. Find the root cause(s) by reading the code. The same kind of gap may exist
   in more than one place, so review every place that consumes a length read
   from the archive, not only the first one you find.
2. Fix the program so malformed archives get the documented safe behaviour.
   Valid archives must keep producing exactly the same output as before
   (the README is the specification, including the rules for empty
   messages, empty fields, trailing bytes and the order of checks).
3. Write regression tests that show the fix works.

Everything here is a local, synthetic exercise: no network, no real software.

## Build and run

    cd src && sh build.sh        # produces ./logpack (gcc -fsanitize=address,undefined -g -O1)
    ./logpack < smoke/NAME.in    # or: ./logpack smoke/NAME.in

`smoke/` (next to this file) has a few valid example inputs with the expected
stdout, to show the I/O format. Input is a command on line 1 followed by the
archive as hex text; see the README.

## Deliverables (write them under `out/`)

* `out/patch/`: the complete fixed copy of `src/` (same layout, built by the
  same `build.sh`, binary name `logpack`)
* `out/tests/`: your regression tests as pairs `NAME.in` / `NAME.out`, where
  `.in` is the program input (command line plus hex) and `.out` is the exact
  stdout the CORRECT program prints (error lines included; they go to stdout)
* `out/REPORT.md`: a short root-cause write-up

## What counts as a failure

A run of the program on an input fails if any of these holds:

* it exits non-zero with an AddressSanitizer or UBSan message on stderr,
* it hangs (10 s limit per run),
* its stdout differs from the expected output, or its exit status differs
  from the documented one for that output (0 for normal output, 1 or 2 as
  listed in the README error table).

A good result is a patch that compiles with `build.sh`, passes the smoke tests
and your own tests with no sanitizer message, and also behaves correctly on
hidden valid and malformed inputs; and tests that would fail on a version of
the program that still has any part of the gap.

Time cap: 45 minutes.
