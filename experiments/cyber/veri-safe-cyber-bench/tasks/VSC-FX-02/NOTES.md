# VSC-FX-02 author notes

Story: tilekit, a toy tile-sheet checker. Script on stdin; commands image/rle/end, crop, tile, scale,
concat, info, drop. Every result prints dimensions + FNV-1a checksum. README documents the limit
(no image above 1<<24 bytes, exactly 1<<24 allowed -> `error: image too large`, exit 3) and the error table.

## The defect (maintenance wording)
Buffer sizes are computed with 32-bit unsigned products that can wrap, while the loops and the rle bounds
use size_t values derived from the same dimensions. The allocation can therefore be much smaller than what
the loops fill, and the documented size limit is never enforced.

## Variants (K=3), one per mutant in private/mutants
* m1_load   (image.c, image_begin): `nbytes = w*h*c` in 32 bits; rle decode is bounded by the 64-bit declared size.
* m2_scale  (ops.c, op_scale): `nbytes = w*fx*h*fy*c` in 32 bits; loops use size_t ow/oh.
* m3_concat (ops.c, op_concat): `nbytes = ow*oh*c` in 32 bits. Wrapping needs the zero-padding behaviour of
  concat (a tall-thin image next to a wide-short one), because two images that each respect the limit would
  otherwise never wrap.

## Intended fix (gold)
`tk_checked_bytes(w,h,c,&n)` in util.c: reject axes above the limit first, then compare `w*h` against
`LIMIT / c` (no overflow, exact boundary), and call it at all three sites before any allocation, with
`error: image too large` / exit 3. Sizes become size_t.

## Traps
* Partial fix: fixing only the visible case (load) leaves scale and concat (RC_edge separates; control d1/d3).
* Checking the 32-bit result after it wrapped (control d2): catches non-wrapping oversize, misses the wrap.
* Over-aggressive: `>=` instead of `>` (exact 1<<24 must work: load, scale, concat all have exact-limit tests,
  and one smoke test is a 16 MiB strip), capping axes (a 1 x 16777216 strip is valid), or ignoring channels
  when checking. Controls e1/e2.
* Validation order: unknown image and bad factor / bad dimensions win over `image too large`
  (ref_tests err_unknown_before_range, err_factor_before_size).
* Aliasing: `scale a a 2 2`, `concat a a a h` must keep working (ref_tests alias_dst).
* A fix that only guards the allocation but still lets `rle` or later loops use huge values would still fail.

## Tests
private/gen_tests.py writes ref_tests (38) and ref_edge (20) from the gold build and cross-checks them
against an independent Python model of the README for all inputs small enough (11 big-image tests are
checked by original==gold instead). ref_tests all pass on the original; ref_edge all fail on the original
(either a sanitizer report, or output instead of the documented rejection). Every mutant fails ref_edge cases.
Scoring: pass = no timeout, no sanitizer message, exact stdout, and documented exit status (see score_task.py).
