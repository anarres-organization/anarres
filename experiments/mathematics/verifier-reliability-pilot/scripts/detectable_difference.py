"""Exact power and minimum detectable difference for the released pairs.

For each released pair the discordant total m = control_only + treatment_only is
fixed and observed. Under an alternative that would move outcomes by d points on
n items, the expected number of control-only flips becomes b = (m + d*n)/2, so
b is Binomial(m, 0.5 + d*n/(2m)) while c = m - b.

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


def exact_p(control_only: int, treatment_only: int) -> float:
    discordant = control_only + treatment_only
    tail = min(control_only, treatment_only)
    cumulative = sum(comb(discordant, k) for k in range(tail + 1)) / (2**discordant)
    return min(1.0, 2 * cumulative)


def power(m: int, n: int, delta_points: float) -> float:
    """Exact power for a difference of delta_points percentage points."""
    shift = delta_points / 100.0 * n
    b_if_true = (m + shift) / 2.0
    if b_if_true <= 0 or b_if_true >= m:
        return 0.0
    p = b_if_true / m
    total = 0.0
    for b in range(m + 1):
        c = m - b
        prob = comb(m, b) * (p**b) * ((1 - p) ** c)
        if exact_p(b, c) <= ALPHA:
            total += prob
    return total


def minimum_detectable(m: int, n: int) -> tuple[float, float]:
    for step in range(0, 121):
        delta = 0.25 * step
        if power(m, n, delta) >= TARGET_POWER:
            return delta, power(m, n, delta)
    return float("inf"), 1.0


def main() -> list[dict]:
    rows = []
    with DATA.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["excluded_from_claims"] != "no":
                continue
            control_only = int(row["control_only"])
            treatment_only = int(row["treatment_only"])
            n = int(row["items"])
            m = control_only + treatment_only
            delta, reached = minimum_detectable(m, n)
            shifted = (m + delta / 100.0 * n) / 2.0
            rows.append(
                {
                    "pair": row["pair"],
                    "items": n,
                    "discordant": m,
                    "observed_gap_points": round(
                        100.0
                        * (int(row["correct_treatment"]) - int(row["correct_control"]))
                        / n,
                        2,
                    ),
                    "min_detectable_points_80pct": delta,
                    "min_detectable_flips": round(shifted - m / 2.0, 2),
                    "power_at_mdd": round(reached, 3),
                }
            )
    for row in rows:
        print(
            f"{row['pair']}: n={row['items']}, discordant={row['discordant']}, "
            f"observed={row['observed_gap_points']:+.2f}pp, "
            f"MDD@80%={row['min_detectable_points_80pct']:.3f}pp "
            f"({row['min_detectable_flips']:.1f} flips), power={row['power_at_mdd']:.3f}"
        )
    return rows


if __name__ == "__main__":
    main()
