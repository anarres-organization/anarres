#!/usr/bin/env python3
"""Print compact endpoint tables from the study record."""

from __future__ import annotations

import csv
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def endpoint_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted((ROOT / "results" / "g1").glob("*_curves.csv")):
        with path.open() as handle:
            for row in csv.DictReader(handle):
                if int(row["step"]) == 128:
                    rows.append(row)
    order = {"1p7": 0, "4b": 1, "8b": 2, "14b": 3}
    return sorted(rows, key=lambda r: (order[r["scale"]], r["cell_short"]))


def print_g1() -> None:
    rows = endpoint_rows()
    print("G=1 step-128 pass@1 (change from scale-matched warm start), percentage points")
    for scale in ("1p7", "4b", "8b", "14b"):
        cells = {r["cell_short"]: r for r in rows if r["scale"] == scale}
        values = []
        for cell in ("HH", "HL", "LH", "LL"):
            row = cells[cell]
            score = (Decimal(row["mean_pass_at_1"]) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
            delta = (Decimal(row["delta_from_pi0"]) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
            values.append(
                f"{cell}={score:.1f} ({delta:+.1f})"
            )
        print(f"{scale:>4}: " + "  ".join(values))


def print_g4() -> None:
    path = ROOT / "results" / "g4" / "endpoint_summary.csv"
    print("\nNative G=4 endpoint robustness, percentage points")
    with path.open() as handle:
        for row in csv.DictReader(handle):
            print(
                f"{row['scale']:>4} {row['policy']:<3} "
                f"per-response={100*float(row['per_response_pass_at_1']):.2f} "
                f"native-pass@4={100*float(row['native_pass_at_4']):.2f}"
            )


if __name__ == "__main__":
    print_g1()
    print_g4()
