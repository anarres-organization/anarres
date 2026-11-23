#!/usr/bin/env python3
"""Recompute exact McNemar tests from released per-pair counts.

Input: data/paired_counts.csv. Each row records two runs scored on the same
300 held-out items: the exclusive set of correct answers for each run, item
counts that decompose exactly, and the two-sided exact p-value reported in the
study README.

The check fails when a stored p-value disagrees with recomputation, so the
README table cannot drift from its inputs.
"""

from __future__ import annotations

import csv
import sys
from math import comb
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "paired_counts.csv"
TOLERANCE = 5e-5


def exact_two_sided(control_only: int, treatment_only: int) -> float:
    """Two-sided exact binomial test over discordant pairs."""
    discordant = control_only + treatment_only
    if discordant == 0:
        return 1.0
    tail = min(control_only, treatment_only)
    cumulative = sum(comb(discordant, k) for k in range(tail + 1)) / (2**discordant)
    return min(1.0, 2 * cumulative)


def main() -> int:
    failures = 0
    with DATA.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            pair = row["pair"]
            items = int(row["items"])
            correct_control = int(row["correct_control"])
            correct_treatment = int(row["correct_treatment"])
            both = int(row["both_correct"])
            control_only = int(row["control_only"])
            treatment_only = int(row["treatment_only"])
            stored = float(row["p_value"])

            if both + control_only != correct_control:
                failures += 1
                print(f"{pair}: control_count_decomposition_failed", file=sys.stderr)
                continue
            if both + treatment_only != correct_treatment:
                failures += 1
                print(f"{pair}: treatment_count_decomposition_failed", file=sys.stderr)
                continue
            if max(correct_control, correct_treatment) > items:
                failures += 1
                print(f"{pair}: counts_exceed_items", file=sys.stderr)
                continue

            recomputed = exact_two_sided(control_only, treatment_only)
            delta = abs(recomputed - stored)
            if delta > TOLERANCE:
                failures += 1
            print(
                f"{pair}: {correct_control / items:.4f} vs "
                f"{correct_treatment / items:.4f}, discordant "
                f"{control_only}/{treatment_only}, p={recomputed:.4g}, "
                f"{'ok' if delta <= TOLERANCE else 'MISMATCH'}"
            )

    if failures:
        print(f"{failures} rows failed verification", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
