#!/usr/bin/env python3
"""Turn the released resolution table into a design budget.

`detectable_difference.py` answers what each released pair could have seen.
This script answers the reverse question: for an effect of a given size, how
many held-out items and how many seed-paired panels does a comparison need
before it reaches 80% power at the same exact two-sided test.

The discordant rate is read from the released counts, so the plan stays tied to
this panel's verifier and policy rather than to an assumed noise level. Each
released pair is first re-solved at its own item count and discordant total, and
the run fails when a solved resolution disagrees with the released table by more
than one search step.

Input: data/paired_counts.csv.
"""

from __future__ import annotations

import csv
from math import exp, lgamma, log, log1p
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "paired_counts.csv"
ALPHA = 0.05
TARGET_POWER = 0.8
STEP = 0.25
PANEL = 300
TARGET_EFFECTS = (2.0, 3.3, 5.0, 9.0)

# Resolution reported by the study README for each pair, in points.
RELEASED = {
    "clean_vs_iid_false_negative": 9.00,
    "clean_vs_group_false_negative": 9.00,
    "clean_vs_no_group_baseline": 10.50,
    "seed_pair_clean": 10.25,
    "seed_pair_open": 10.25,
}


def _log_choose(n: int, k: int) -> float:
    return lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1)


def critical_flips(m: int) -> int:
    """Largest tail count the two-sided exact test rejects at ALPHA."""
    cumulative = 0.0
    limit = -1
    half = m // 2
    for k in range(half + 1):
        cumulative += exp(_log_choose(m, k) - m * log(2.0))
        if 2 * cumulative <= ALPHA:
            limit = k
        else:
            break
    return limit


def power(m: int, n: int, delta_points: float, limit: int | None = None) -> float:
    """Exact power for a difference of delta_points, one discordant total."""
    shift = delta_points / 100.0 * n
    mean = (m + shift) / 2.0
    if mean <= 0 or mean >= m:
        return 0.0
    p = mean / m
    limit = critical_flips(m) if limit is None else limit
    if limit < 0:
        return 0.0
    lp, lq = log(p), log1p(-p)
    total = 0.0
    for b in range(limit + 1):
        total += exp(_log_choose(m, b) + b * lp + (m - b) * lq)
    for b in range(m - limit, m + 1):
        total += exp(_log_choose(m, b) + b * lp + (m - b) * lq)
    return total


def minimum_detectable(m: int, n: int) -> float:
    limit = critical_flips(m)
    for step in range(0, 121):
        delta = STEP * step
        if power(m, n, delta, limit) >= TARGET_POWER:
            return delta
    return float("inf")


def items_for(delta_points: float, rate: float) -> int:
    """Smallest item count whose exact power reaches the target."""
    low, high = 100, 8192
    while low < high:
        mid = (low + high) // 2
        if power(max(2, round(rate * mid)), mid, delta_points) >= TARGET_POWER:
            high = mid
        else:
            low = mid + 1
    return low


def main() -> int:
    rows = [row for row in csv.DictReader(DATA.open(newline="", encoding="utf-8"))]
    counted = [row for row in rows if row["excluded_from_claims"] == "no"]
    failures = 0
    for row in counted:
        pair = row["pair"]
        n = int(row["items"])
        m = int(row["control_only"]) + int(row["treatment_only"])
        solved = minimum_detectable(m, n)
        expected = RELEASED.get(pair)
        status = "ok"
        if expected is not None and abs(expected - solved) > STEP:
            status = f"MISMATCH (released {expected:.2f})"
            failures += 1
        print(
            f"{pair}: n={n}, discordant={m}, rate={m / n:.3f}, "
            f"solved resolution={solved:.2f}pp, {status}"
        )

    items = sum(int(row["items"]) for row in counted)
    flips = sum(int(row["control_only"]) + int(row["treatment_only"]) for row in counted)
    rate = flips / items

    print()
    print(f"pooled discordant rate over {len(counted)} pairs: {rate:.3f}")
    print("DESIGN BUDGET")
    for delta in TARGET_EFFECTS:
        needed = items_for(delta, rate)
        panels = -(-needed // PANEL)
        print(
            f"effect {delta:.2f}pp: items={needed}, "
            f"seed-paired {PANEL}-item panels={panels}, "
            f"discordant at that size={round(rate * needed)}"
        )

    seed_band = max(
        abs(int(row["correct_treatment"]) - int(row["correct_control"])) / int(row["items"]) * 100
        for row in counted
        if row["pair"].startswith("seed_pair")
    )
    print()
    print(f"largest recorded same-configuration seed shift: {seed_band:.2f}pp")
    print("VERDICT GATE")
    for row in counted:
        pair = row["pair"]
        if pair.startswith("seed_pair"):
            continue
        n = int(row["items"])
        observed = (int(row["correct_treatment"]) - int(row["correct_control"])) / n
        observed *= 100
        resolved = minimum_detectable(int(row["control_only"]) + int(row["treatment_only"]), n)
        if abs(observed) < resolved:
            verdict = "unresolved below this design's resolution"
        elif abs(observed) <= seed_band:
            verdict = "inside the recorded seed spread"
        else:
            verdict = "attributable: exceeds resolution and seed spread"
        print(
            f"{pair}: observed={observed:+.2f}pp, resolution={resolved:.2f}pp, "
            f"seed band={seed_band:.2f}pp, verdict={verdict}"
        )
    print("seed pairs measure that band rather than an intervention and are scored above")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
