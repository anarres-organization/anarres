# NOTES VSC-FX-03 (docvault, Python 3.12, split val, K=3)

Synthetic, local-only. The program serves files from a temp-dir vault; nothing touches the network or the host
outside the temp dir (the scorer refuses setup headers whose links leave the temp dir).

## The defect (maintenance wording)
The directory containment check is incomplete. Three places differ from the documented contract
("anything that resolves outside the user's folder is `DENIED: outside root`, status 4"):

1. **Single-file commands (READ, and RUN's script lookup)** use `Session._locate_file`, which checks the joined path
   *text* (`joined.startswith(user_root)`) and never the resolved location. Paths that climb out with `..`, links that
   point elsewhere and sibling folders are not rejected. Variant 1.
2. **LIST** checks the argument as typed, before alias expansion, and then lists the expanded target without a new check.
   An alias whose target leaves the folder (or names a link that does) is listed. Variant 2.
3. **EXPORT** checks each path argument after alias expansion, but `archive.collect` then expands folders (following
   links) and never re-checks what it reaches. Variant 3.

All three end in the program's own invariant check (`guard.py`, exit 86) in the original, because `guard` re-checks every
read/write/listing against the user root.

## Intended fix
One resolve-and-contain helper (`vpaths.resolve_real`: realpath, then `commonpath`/prefix-with-separator test) used by
every command *after* alias expansion; `archive.collect` checks every real path it reaches and raises `Denied`
(whole EXPORT is rejected, nothing written). Gold in `private/gold/`.

## Traps
* Obvious partial fix: normalise `..` in the READ text check (handles the visible case; control (d), RC_edge 0.33).
  Symlinks (e02, e03), alias in LIST (e05), export expansion (e06-e08), nested script (e09) still fail.
* Prefix trap: `real.startswith(user_root)` lets the sibling folder `alice2` through for user `alice` (e04, e10; control g).
* Over-aggressive fixes: reject any `..` text, any link, any leading `/`, or names that merely contain dots
  (`..dots.txt`, `a..b.txt`); also `LIST .` must still work (real == user root). Covered by ref_tests t02, t03, t05, t08, t14, t15.
* Check order: containment before existence (missing target outside the folder is DENIED, not "not found"), e01/e02.
* Nested RUN: child sessions copy user and aliases, changes do not leak; after the fix a script cannot widen access (e09, e11).
* EXPORT dedups by real path, skips the `exports/` folder, handles link loops: a rewrite of collect must keep this (t08, t09, t15).

## Why each mutant exists (private/mutants/)
* m1_read_text_check: re-introduces the text check in `_locate_file` (kills need an escape via `..`, link, sibling, or other user).
* m2_list_pre_expansion: LIST validates before alias expansion (needs a test with an alias leaving the folder, or an alias to a link out; also hit through RUN in e09).
* m3_export_members: `collect` stops re-checking (needs a folder holding a link that leads out; e06-e08).
Every mutant fails at least one ref_edge case and no ref_tests case. The original fails all 12 ref_edge cases.

## Test format
`NAME.in` starts (anywhere) with `#! dir|file|link` setup lines applied to a fresh temp dir; the program ignores them as
comments; see the docstring of `private/score_task.py` and `public/INSTRUCTION.md`. Hidden cases also have `NAME.code`
(exit status). Agent tests are accepted with exit status 0, 2 or 4 and a clean stderr.
`sh private/build_private.sh` rebuilds all expected files from gold.
