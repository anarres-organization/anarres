#!/usr/bin/env python3
"""Recompute the prospective SylloGym decision from compact public inputs."""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTCOMES = ROOT / "data" / "outcomes.json"
FREEZE = ROOT / "data" / "frozen-decision.json"
EXPECTED = ROOT / "results" / "summary.json"
T_CRITICAL_DF2_95 = 4.302652729911275


def rounded(value: float) -> float:
    """Round derived values for deterministic public output."""
    return round(value, 6)


def paired_contrast(left: list[float], right: list[float]) -> dict[str, object]:
    """Return a paired training-seed contrast and t interval."""
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


def compute(outcomes: dict[str, object], freeze: dict[str, object]) -> dict[str, object]:
    """Compute means, regret, contrasts, guardrails, and the frozen decision."""
    grouped: dict[str, dict[int, float]] = {}
    for row in outcomes["records"]:
        grouped.setdefault(row["arm"], {})[row["seed"]] = row["completion_percent"]

    values = {
        arm: [seed_values[seed] for seed in sorted(seed_values)]
        for arm, seed_values in sorted(grouped.items())
    }
    means = {arm: statistics.mean(scores) for arm, scores in values.items()}
    observed_best = max(means, key=means.get)
    best_mean = means[observed_best]
    selected = "frozen_policy_response_allocation"
    published = "published_depth_weighted_control"
    uniform = "uniform_14_task_control"
    contrasts = {
        "policy_response_minus_published": paired_contrast(values[selected], values[published]),
        "policy_response_minus_uniform": paired_contrast(values[selected], values[uniform]),
    }

    threshold = freeze["decision_thresholds"]["material_family_regression_percentage_points"]
    family_values = [
        value
        for comparison in outcomes["family_guardrail_deltas_pp"].values()
        for value in comparison.values()
    ]
    minimum_family_delta = min(family_values)
    no_material_regression = minimum_family_delta > threshold
    sesoi = freeze["decision_thresholds"]["sesoi_percentage_points"]
    success = (
        all(contrast["mean"] >= sesoi and contrast["t95"][0] > 0 for contrast in contrasts.values())
        and no_material_regression
    )
    harm = any(contrast["mean"] <= -sesoi for contrast in contrasts.values()) or not (
        no_material_regression
    )
    decision = "success" if success else "harm" if harm else "abstain"

    return {
        "artifact": "prospective_syllogym_environment_selection_summary_v1",
        "allocation_regret_pp": {
            arm: rounded(best_mean - mean) for arm, mean in sorted(means.items())
        },
        "contrasts": contrasts,
        "decision": decision,
        "frozen_selection": selected,
        "frozen_selection_regret_pp": rounded(best_mean - means[selected]),
        "independent_training_seeds": len(outcomes["contract"]["training_seeds"]),
        "means_pp": {arm: rounded(mean) for arm, mean in sorted(means.items())},
        "minimum_family_guardrail_delta_pp": rounded(minimum_family_delta),
        "no_material_family_regression": no_material_regression,
        "observed_best": observed_best,
        "sesoi_pp": sesoi,
        "warm_start_task_macro_pp": rounded(outcomes["warm_start_task_macro_percent"]),
    }


def main() -> None:
    """Print the derived summary and verify the committed result."""
    outcomes = json.loads(OUTCOMES.read_text())
    freeze = json.loads(FREEZE.read_text())
    actual = compute(outcomes, freeze)
    expected = json.loads(EXPECTED.read_text())
    if actual != expected:
        raise SystemExit("recomputed summary does not match results/summary.json")
    print(json.dumps(actual, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
