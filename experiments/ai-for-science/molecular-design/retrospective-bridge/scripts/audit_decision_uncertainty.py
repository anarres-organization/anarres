#!/usr/bin/env python3
"""Bootstrap molecular allocation metrics over complete held-out contexts."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

RESAMPLES = 20_000
RANDOM_SEED = 20261112


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected an object: {path}")
    return value


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def context_values(
    selections: list[dict[str, Any]], context_key: str
) -> dict[str, tuple[float, float]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in selections:
        grouped[str(row[context_key])].append(row)
    values = {}
    for context, rows in sorted(grouped.items()):
        values[context] = (
            mean(float(row["normalized_regret"]) for row in rows),
            mean(float(row["selected_method"] in row["observed_best_methods"]) for row in rows),
        )
    return values


def paired_bootstrap(
    primary: dict[str, tuple[float, float]],
    baseline: dict[str, tuple[float, float]],
    *,
    rng: random.Random,
) -> dict[str, Any]:
    if set(primary) != set(baseline):
        raise ValueError("primary and baseline contexts differ")
    contexts = sorted(primary)
    if len(contexts) < 2:
        raise ValueError("at least two independent contexts are required")
    primary_regrets = []
    primary_credits = []
    regret_differences = []
    credit_differences = []
    for _ in range(RESAMPLES):
        sample = [rng.choice(contexts) for _ in contexts]
        primary_regret = mean(primary[context][0] for context in sample)
        baseline_regret = mean(baseline[context][0] for context in sample)
        primary_credit = mean(primary[context][1] for context in sample)
        baseline_credit = mean(baseline[context][1] for context in sample)
        primary_regrets.append(primary_regret)
        primary_credits.append(primary_credit)
        regret_differences.append(primary_regret - baseline_regret)
        credit_differences.append(primary_credit - baseline_credit)
    return {
        "independent_contexts": len(contexts),
        "resamples": RESAMPLES,
        "primary_mean_normalized_regret_95_interval": [
            percentile(primary_regrets, 0.025),
            percentile(primary_regrets, 0.975),
        ],
        "primary_best_choice_credit_95_interval": [
            percentile(primary_credits, 0.025),
            percentile(primary_credits, 0.975),
        ],
        "primary_minus_baseline_regret_95_interval": [
            percentile(regret_differences, 0.025),
            percentile(regret_differences, 0.975),
        ],
        "primary_minus_baseline_best_choice_credit_95_interval": [
            percentile(credit_differences, 0.025),
            percentile(credit_differences, 0.975),
        ],
        "bootstrap_frequency_primary_lower_regret": mean(
            float(value < 0) for value in regret_differences
        ),
        "bootstrap_frequency_primary_higher_best_choice_credit": mean(
            float(value > 0) for value in credit_differences
        ),
    }


def build(data: Path) -> dict[str, Any]:
    vantilborg = load(data / "vantilborg_active_learning_bridge_v1.json")
    reisman = load(data / "reisman_regioselectivity_bridge_v1.json")
    van_audit = vantilborg["leave_one_dataset_out"]
    reisman_audit = reisman["stable_top1_decision_audit"]
    rng = random.Random(RANDOM_SEED)
    return {
        "schema_version": "anarres.molecular-decision-uncertainty.v1",
        "method": {
            "resampling_unit": (
                "complete held-out molecular library or target; candidate arms within a "
                "context are never resampled independently"
            ),
            "interval": "paired nonparametric percentile bootstrap",
            "random_seed": RANDOM_SEED,
            "resamples": RESAMPLES,
            "pairwise_accuracy_interval": (
                "not reported because pairwise comparisons within a context are dependent"
            ),
        },
        "vantilborg_cross_library": paired_bootstrap(
            context_values(van_audit["method_by_architecture"]["selections"], "dataset"),
            context_values(vantilborg["training_fold_fixed_method"]["selections"], "dataset"),
            rng=rng,
        ),
        "reisman_cross_target_nearest": paired_bootstrap(
            context_values(
                reisman_audit["structural_nearest_target"]["selections"], "target_smiles"
            ),
            context_values(
                reisman_audit["training_fold_fixed_method"]["selections"], "target_smiles"
            ),
            rng=rng,
        ),
        "reisman_cross_target_nested": paired_bootstrap(
            context_values(
                reisman_audit["nested_similarity_weighted"]["selections"], "target_smiles"
            ),
            context_values(
                reisman_audit["training_fold_fixed_method"]["selections"], "target_smiles"
            ),
            rng=rng,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build(args.data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
