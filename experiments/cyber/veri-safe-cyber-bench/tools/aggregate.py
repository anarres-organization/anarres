#!/usr/bin/env python3
"""Aggregate per-task factor JSON into the four metrics (harsh int, smooth int, harsh int_ref, smooth int_ref).
usage: aggregate.py results.json   (list of {"task":..., "IC_tests":..,"IC_fix":..,"VC":..,"RC_tests":..,"RC_edge":..})
Harsh = 1 iff every factor of the group >= 0.98 (1 means saturated, so lower is harder). Smooth = geometric mean of per-factor
averages over all tasks (N=3 int, N=5 int_ref)."""
import json, sys, math
rows = json.load(open(sys.argv[1]))
INT = ["IC_tests", "IC_fix", "VC"]; REF = INT + ["RC_tests", "RC_edge"]
def harsh(r, fs): return int(all(r[f] >= 0.98 for f in fs))
def smooth(rs, fs):
    p = 1.0
    for f in fs: p *= sum(r[f] for r in rs) / len(rs)
    return p ** (1 / len(fs))
for r in rows:
    print(f'{r["task"]}: harsh_int={harsh(r,INT)} harsh_int_ref={harsh(r,REF)} ' + " ".join(f"{f}={r[f]:.2f}" for f in REF))
n = len(rows)
print(f'Harsh int: {sum(harsh(r,INT) for r in rows)}/{n} saturated')
print(f'Smooth int (N=3): {smooth(rows,INT):.3f}')
print(f'Harsh int_ref: {sum(harsh(r,REF) for r in rows)}/{n} saturated')
print(f'Smooth int_ref (N=5): {smooth(rows,REF):.3f}')
