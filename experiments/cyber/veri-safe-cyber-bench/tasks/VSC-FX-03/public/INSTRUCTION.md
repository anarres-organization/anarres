# Task VSC-FX-03: docvault containment check (Python 3.12, stdlib only)

You are maintaining `docvault`, a small document-store command line tool (see
`src/README.md` for the product story and the documented behaviour). Users
report that the check which keeps a user inside their own folder is incomplete:
it is done on the unresolved joined path text in some commands, handles aliases
and nested commands inconsistently, and one export path does not re-check after
expansion. The documented behaviour (README, "Safe behaviour") is the target.

Find the root cause(s) by reading the code, fix them without changing any valid
behaviour, and write regression tests that show the fix works. Several commands
are affected; a fix that handles only the most visible case is not enough, and a
fix that rejects requests which are actually fine will break valid use.

## Deliverables (directory `out/`)
* `out/patch/` the complete fixed copy of `src/` (same layout; it must pass `sh build.sh`)
* `out/tests/` your regression tests as pairs `NAME.in` / `NAME.out`, where `NAME.out` is the exact stdout the CORRECT program prints for `NAME.in`
* `out/REPORT.md` a short root-cause write-up

## Running
* Build: `sh build.sh` (inside the source directory; compile check only)
* Run: `python3 docvault.py vault < NAME.in` with a fresh temporary directory as the working directory
* Smoke examples with expected stdout: `smoke/*.in`, `smoke/*.out`

## Test file format
`NAME.in` is the stdin of one run. Its leading lines that start with `#! ` form
a setup header that the harness applies to the fresh temp directory before the
run (docvault ignores them because they start with `#`):

    #! dir  PATH                   create a folder
    #! file PATH | CONTENT         create a file; CONTENT may use \n \t \\ escapes
                                   (no " | " part means an empty file)
    #! link PATH -> TARGET         create a symbolic link whose text is TARGET
                                   ($TMP stands for the temp dir path)

PATH is relative to the temp dir (for example `vault/users/alice/notes.txt`).
The vault root is `vault`. Link targets must stay inside the temp dir; a test
whose header breaks this rule is invalid and counts as failing. Keep files
ASCII. Header lines may be mixed freely with command lines but are normally
placed first.

## Failure definition
A run FAILS if any of these hold: the program's invariant check fires (exit
code 86 with `INVARIANT:` on stderr), it crashes with a traceback, it takes
longer than 10 s, its exit code is not 0, 2 or 4, or its stdout differs from the
expected output.

## Scoring (for your information)
Your tests must fail on the original program and pass on your patch (at least
one of them must fail on the original); your patch must build and pass all
smoke examples and all your tests; your tests are also run against variants of
the program that re-introduce parts of the defect, and are measured by how many
of those variants they detect; a hidden reference suite checks the patch on
valid and on documented-safe-behaviour cases.

Time cap: 45 minutes.
