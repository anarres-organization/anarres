#!/usr/bin/env python3
"""Recompute the prospective PushT decision summary from compact outcomes."""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "outcomes.json"
EXPECTED = ROOT / "results" / "summary.json"
T_CRITICAL_DF2_95 = 4.302652729911275


def canonical_json(value: dict[str, object]) -> str:
    """Serialize one released artifact in its byte-stable form."""
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def rounded(value: float) -> float:
    """Round derived values for a stable, readable public artifact."""
    return round(value, 6)


def paired_contrast(left: list[float], right: list[float]) -> dict[str, object]:
    """Return a paired three-seed contrast and its t interval."""
    deltas = [a - b for a, b in zip(left, right, strict=True)]
    mean = statistics.mean(deltas)
    sd = statistics.stdev(deltas)
    half_width = T_CRITICAL_DF2_95 * sd / math.sqrt(len(deltas))
    return {
        "deltas": [rounded(value) for value in deltas],
        "mean": rounded(mean),
        "positive_seeds": sum(value > 0 for value in deltas),
        "sd": rounded(sd),
        "t95": [rounded(mean - half_width), rounded(mean + half_width)],
    }


def compute(data: dict[str, object]) -> dict[str, object]:
    """Compute the complete public summary."""
    records = data["records"]
    grouped: dict[str, dict[int, float]] = {}
    for row in records:
        grouped.setdefault(row["arm"], {})[row["seed"]] = row["success_percent"]

    values = {
        arm: [seed_values[seed] for seed in sorted(seed_values)]
        for arm, seed_values in sorted(grouped.items())
    }
    means = {arm: statistics.mean(scores) for arm, scores in values.items()}
    observed_best = max(means, key=means.get)
    best_mean = means[observed_best]
    frozen_set = data["chronology"]["frozen_candidate_set"]

    return {
        "artifact": "prospective_pusht_environment_selection_summary_v1",
        "abstention_correct": observed_best in frozen_set,
        "arm_regret_pp": {arm: rounded(best_mean - mean) for arm, mean in sorted(means.items())},
        "contrasts": {
            "calibra_minus_diversity": paired_contrast(
                values["calibra_retain_25"], values["diversity_only_retain_25"]
            ),
            "calibra_minus_random": paired_contrast(
                values["calibra_retain_25"], values["random_full_retain_25"]
            ),
            "diversity_minus_random": paired_contrast(
                values["diversity_only_retain_25"], values["random_full_retain_25"]
            ),
        },
        "frozen_action": data["chronology"]["frozen_action"],
        "independent_training_seeds": len(data["contract"]["training_seeds"]),
        "means": {arm: rounded(mean) for arm, mean in sorted(means.items())},
        "observed_best": observed_best,
    }


def main() -> None:
    """Print the recomputed summary and verify the committed result."""
    data = json.loads(INPUT.read_text())
    actual = compute(data)
    serialized = canonical_json(actual)
    if serialized != EXPECTED.read_text():
        raise SystemExit("recomputed summary does not byte-match results/summary.json")
    print(serialized, end="")


if __name__ == "__main__":
    main()
