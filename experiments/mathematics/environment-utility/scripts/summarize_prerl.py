#!/usr/bin/env python3
"""Recompute the study's Stage-D pre-RL coordinates from response metadata."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "prerl_measurements"
OUTPUT = ROOT / "results" / "mechanism" / "prerl_rho_h.csv"


def summarize(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text())
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in payload["detail"]:
        grouped[row["example_id"]].append(row)

    group_masses: list[float] = []
    total_tokens = 0
    mixed = 0
    admitted = 0
    successes = 0
    responses = 0
    for rows in grouped.values():
        rewards = [float(bool(r["math_correct"])) for r in rows]
        mean_reward = sum(rewards) / len(rewards)
        mixed += int(0 < sum(rewards) < len(rewards))
        mass = 0.0
        for row, reward in zip(rows, rewards):
            total_tokens += int(row["num_tokens"])
            responses += 1
            successes += int(reward)
            is_admitted = not bool(row["truncated"])
            admitted += int(is_admitted)
            if is_admitted:
                mass += abs(reward - mean_reward)
        group_masses.append(mass)

    total_mass = sum(group_masses)
    denom = len(group_masses) * sum(x * x for x in group_masses)
    coverage = (total_mass * total_mass / denom) if denom else 0.0
    return {
        "scale": path.parent.name,
        "cell": path.stem,
        "groups": len(grouped),
        "responses": responses,
        "success_rate": successes / responses,
        "mixed_group_rate": mixed / len(grouped),
        "admission_rate": admitted / responses,
        "mean_generated_tokens": total_tokens / responses,
        "admitted_advantage_mass": total_mass,
        "rho_per_million_generated_tokens": 1_000_000 * total_mass / total_tokens,
        "H_effective_prompt_coverage": coverage,
    }


def main() -> None:
    rows = [summarize(path) for path in sorted(INPUT.glob("*/*.json"))]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({len(rows)} cells)")
    for row in rows:
        print(
            f"{row['scale']:>4} {row['cell']:<26} "
            f"rho={row['rho_per_million_generated_tokens']:.4f} "
            f"H={row['H_effective_prompt_coverage']:.4f}"
        )


if __name__ == "__main__":
    main()
