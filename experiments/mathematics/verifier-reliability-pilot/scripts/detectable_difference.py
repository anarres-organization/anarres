"""Exact power and minimum detectable difference for the released pairs.

For each released pair the discordant total m = control_only + treatment_only is
fixed and observed. Under an alternative that would move outcomes by d points on
n items, the expected number of control-only flips becomes b = (m + d*n)/2, so
b follows Binomial(m, 0.5 + d*n/(2m)) while c = m - b.

Rejection follows the same two-sided exact binomial test the study uses. Power is
the exact sum over that binomial law, with no normal approximation and no
simulation. The smallest d reaching 0.8 defines the resolution of the pair.
"""

from __future__ import annotations

import csv
from math import comb
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "paired_counts.csv"
ALPHA = 0.05
TARGET_POWER = 0.8


def exact_two_sided(control_only: int, treatment_only: int) -> float:
    discordant = control_only + treatment_only
    tail = min(control_only, treatment_only)
    cumulative = sum(comb(discordant, k) for k in range(tail + 1)) / (2**discordant)
    return min(1.0, 2 * cumulative)


def power(m: int, n: int, delta_points: float) -> float:
    """Exact power for a difference of delta_points percentage points."""
    shift = delta_points / 100.0 * n
    b_mean = (m + shift) / 2.0
    if b_mean <= 0 or b_mean >= m:
        return 0.0
    p = b_mean / m
    total = 0.0
    for b in range(m + 1):
        c = m - b
        probability = comb(m, b) * (p**b) * ((1 - p) ** c)
        if exact_two_sided(b, c) <= ALPHA:
            total += probability
    return total


def minimum_detectable(m: int, n: int) -> tuple[float, float]:
    for step in range(0, 121):
        delta = 0.25 * step
        reached = power(m, n, delta)
        if reached >= TARGET_POWER:
            return delta, reached
    return float("inf"), 1.0


def main() -> int:
    with DATA.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["excluded_from_claims"] != "no":
                continue
            n = int(row["items"])
            control_only = int(row["control_only"])
            treatment_only = int(row["treatment_only"])
            m = control_only + treatment_only
            delta, reached = minimum_detectable(m, n)
            flips = (m + delta / 100.0 * n) / 2.0 - m / 2.0
            observed = 100.0 * (
                int(row["correct_treatment"]) - int(row["correct_control"])
            ) / n
            print(
                f"{row['pair']}: n={n}, discordant={m}, observed={observed:+.2f}pp, "
                f"smallest detectable={delta:.2f}pp ({flips:.1f} flips), "
                f"power={reached:.3f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
