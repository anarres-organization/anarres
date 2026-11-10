#!/usr/bin/env python3
"""Recompute the released Can v1.4.1 prospective result."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import statistics
from pathlib import Path
from typing import Any

ARMS = (
    "all_data",
    "random_50",
    "length_50",
    "cupid_50",
    "cupid_tier_balanced_50",
)
SEEDS = (1101, 1102, 1103, 1104, 1105)


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = quantile * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def exact_bootstrap_interval(values: list[float]) -> list[float]:
    means = [
        statistics.fmean(values[index] for index in indices)
        for indices in itertools.product(range(len(values)), repeat=len(values))
    ]
    return [percentile(means, 0.025), percentile(means, 0.975)]


def validate_and_index(
    outcomes: dict[str, Any], release_gate: dict[str, Any]
) -> dict[str, dict[int, float]]:
    if outcomes.get("schema_version") != "anarres.robotics-cupid-released-outcomes.v1":
        raise ValueError("unsupported released-outcome schema")
    if release_gate.get("status") != "RELEASE_GATE_PASSED__OUTCOMES_MAY_BE_OPENED":
        raise ValueError("release gate did not pass")
    gate_hashes = {record["name"]: record["outcome_sha256"] for record in release_gate["records"]}
    if len(gate_hashes) != 25 or release_gate.get("evaluation_episodes") != 2500:
        raise ValueError("release gate does not contain the complete 25-run panel")

    by_arm: dict[str, dict[int, float]] = {arm: {} for arm in ARMS}
    seen_runs: set[str] = set()
    for record in outcomes.get("records", []):
        arm = record["candidate_id"]
        seed = int(record["seed"])
        run_id = record["run_id"]
        rate = float(record["success_rate"])
        if arm not in by_arm or seed not in SEEDS:
            raise ValueError(f"unexpected candidate or seed: {arm}/{seed}")
        if run_id != f"dp_can_{arm}_seed{seed}" or run_id in seen_runs:
            raise ValueError(f"invalid or duplicate run identity: {run_id}")
        if record.get("evaluation_episodes") != 100 or not 0.0 <= rate <= 1.0:
            raise ValueError(f"invalid evaluation record: {run_id}")
        if gate_hashes.get(run_id) != record.get("outcome_sha256"):
            raise ValueError(f"outcome hash differs from the release gate: {run_id}")
        seen_runs.add(run_id)
        by_arm[arm][seed] = rate
    if seen_runs != set(gate_hashes):
        raise ValueError("released outcomes do not cover the complete gated panel")
    return by_arm


def compute(
    outcomes: dict[str, Any], release_gate: dict[str, Any], frozen: dict[str, Any]
) -> dict[str, Any]:
    by_arm = validate_and_index(outcomes, release_gate)
    prediction = frozen["decision"]
    if prediction not in ARMS:
        raise ValueError("frozen decision is absent from the released panel")

    means = {arm: statistics.fmean(values.values()) for arm, values in by_arm.items()}
    best_mean = max(means.values())
    best_arms = sorted(arm for arm, value in means.items() if value == best_mean)
    paired = {}
    for comparator in ARMS:
        if comparator == prediction:
            continue
        differences = [by_arm[prediction][seed] - by_arm[comparator][seed] for seed in SEEDS]
        paired[comparator] = {
            "prediction_minus_comparator_by_seed": differences,
            "mean_difference": statistics.fmean(differences),
            "exact_seed_bootstrap_95_interval": exact_bootstrap_interval(differences),
        }

    pairwise = []
    for left, right in itertools.combinations(ARMS, 2):
        differences = [by_arm[left][seed] - by_arm[right][seed] for seed in SEEDS]
        pairwise.append(
            {
                "left": left,
                "right": right,
                "mean_difference": statistics.fmean(differences),
                "seed_wins_left": sum(value > 0 for value in differences),
                "seed_ties": sum(value == 0 for value in differences),
                "seed_wins_right": sum(value < 0 for value in differences),
                "exact_seed_bootstrap_95_interval": exact_bootstrap_interval(differences),
            }
        )

    return {
        "status": "COMPLETE_PROSPECTIVE_PANEL_SCORED",
        "frozen_prediction": prediction,
        "success_rate_by_arm_and_seed": {
            arm: {str(seed): rate for seed, rate in values.items()}
            for arm, values in by_arm.items()
        },
        "mean_success_rate_by_arm": means,
        "best_arm_by_mean": best_arms,
        "allocation_regret": best_mean - means[prediction],
        "paired_prediction_contrasts": paired,
        "all_pairwise_contrasts": pairwise,
        "uncertainty_note": (
            "Intervals resample the five paired training seeds exactly; rollout episodes are not "
            "treated as independent interventions."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    result = compute(
        json.loads((root / "OUTCOMES.json").read_text(encoding="utf-8")),
        json.loads((root / "RELEASE_GATE.json").read_text(encoding="utf-8")),
        json.loads((root / "CANDIDATES.json").read_text(encoding="utf-8")),
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
