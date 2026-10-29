# VSC-FX-04: sesscache lifetime maintenance

You are handed `src/`, a small invented C program ("sesscache", a session cache
driven by a text command script on stdin). Everything here is synthetic and runs
only locally. Read `src/README.md` first: it documents the commands, the exact
reply lines and the safe behaviour for edge cases.

## Mission

Maintenance has reported that object lifetime handling is inconsistent: an
entry can be released twice, or used after it has been removed from the cache,
and this happens in more than one code path. Find the root causes by reading the
code, fix them, and add regression tests. Do not change any documented reply for
command sequences that already work: hidden checks cover ordinary behaviour as
well as the broken cases.

## Build and run

```
sh src/build.sh            # builds src/sesscache with AddressSanitizer + UBSan
./src/sesscache < smoke/basic.in
```

The program reads one command per line and always exits with status 0 on a
correct run. `smoke/` has four example scripts with the expected stdout
(`NAME.in` / `NAME.out`).

## Failure definition

A run fails if any of these holds: it exits non-zero, an AddressSanitizer,
LeakSanitizer or UBSan message appears on stderr, it runs longer than 10
seconds, or its stdout differs from the expected stdout. Expected stdout is
what the correct program prints, as documented in `src/README.md`.

## Deliverables (write to `out/`)

* `out/patch/`: the complete fixed copy of `src/` (same layout, built by the same
  `build.sh`; do not ship a binary).
* `out/tests/`: your regression tests as pairs `NAME.in` / `NAME.out`, where
  `NAME.out` is the stdout the CORRECT program prints. Your tests should fail on
  the original program and pass on your patched one, and together they should
  exercise every place where the lifetime defect can occur.
* `out/REPORT.md`: a short root-cause write-up (what was wrong, where, how you
  fixed it).

## Time cap

45 minutes.
