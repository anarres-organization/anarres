# Task VSC-FX-02: tilekit size handling

You maintain `tilekit`, a small C tool that reads a text description of a tile
sheet and performs crop, tile, scale and concatenate operations, printing
dimensions and a checksum for every result. Read `src/README.md` first: it is
the specification, including the size limit and the error messages and exit
codes. Everything here is a synthetic toy program, run only in a local sandbox.

## Maintenance ticket

QA reports that on some very large sheet descriptions the sanitizer build of
`tilekit` stops with a heap error, and that on others it prints results for
images that are larger than the documented 1<<24 byte limit instead of
rejecting them with `error: image too large` (exit status 3). The buffer size
calculations in the code do not always agree with the sizes that the loops
that fill those buffers use. The same kind of mistake may occur in more than
one place, so look at every place where a buffer is sized.

Your job:

1. Find the root cause(s) by reading the code in `src/`.
2. Fix the program so that it follows the README for all inputs, without
   changing the behaviour for valid input (including images of exactly
   1<<24 bytes, and the output format).
3. Write regression tests that show the fix works.

## Deliverable (`out/`)

* `out/patch/`: the complete fixed copy of `src/` (same layout, built by the same `build.sh`).
* `out/tests/`: your regression tests as pairs `NAME.in` / `NAME.out`, where
  `NAME.in` is a script for stdin and `NAME.out` is the exact stdout the
  CORRECT program prints.
* `out/REPORT.md`: a short root-cause write-up (what was wrong, where, how you fixed it, what you tested).

## Build and test

    cd src && ./build.sh           # gcc -fsanitize=address,undefined -g -O1, produces ./tilekit
    ./tilekit < smoke/NAME.in      # compare stdout with smoke/NAME.out

(`smoke/` is next to `src/`.) The compiler is `gcc`; no network is needed. Tests
may use sizes up to the documented limit; keep each test fast (well under 10 seconds).

## What counts as a failure

A run of a test fails if any of these holds:

* the program exits non-zero with an AddressSanitizer or UBSan message on stderr, or it hangs (10 s limit);
* stdout differs from the expected output;
* the exit status differs from the documented one for the last output line
  (0 normally; 1 for `error: syntax` and `error: unterminated image`; 3 for
  `error: image too large`; 2 for every other `error:` line).

Leak reports are not counted. Your patch must pass every smoke test and every
test you wrote, and your tests should fail on the original program for the
defects you found.

## Time cap

45 minutes.
