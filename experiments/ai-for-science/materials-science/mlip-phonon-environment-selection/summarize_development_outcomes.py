#!/usr/bin/env python3
"""Validate and compact the frozen development checkpoint evaluation matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_result(path: Path, material_id: str) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    if result["material_id"] != material_id or result["backend"] != "nequix":
        raise ValueError(f"evaluation identity mismatch: {path}")
    metrics = result["metrics"]
    required = (
        "frequency_mae_thz",
        "frequency_rmse_thz",
        "reference_stability_margin_kelvin",
        "predicted_stability_margin_kelvin",
    )
    if not all(math.isfinite(float(metrics[key])) for key in required):
        raise ValueError(f"non-finite evaluation result: {path}")
    return result


def summarize(
    contract_path: Path,
    roles_path: Path,
    starting_targets_path: Path,
    evaluation_root: Path,
) -> dict:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    roles = json.loads(roles_path.read_text(encoding="utf-8"))
    starting = json.loads(starting_targets_path.read_text(encoding="utf-8"))
    development_targets = roles["roles"]["development"]
    starting_by_id = {
        row["material_id"]: row for row in starting["targets"] if row["role"] == "development"
    }
    if set(starting_by_id) != set(development_targets):
        raise ValueError("starting checkpoint does not cover the development targets")
    baseline_mean = sum(row["frequency_mae_thz"] for row in starting_by_id.values()) / len(
        starting_by_id
    )

    seed_rows = []
    target_final = defaultdict(dict)
    expected_files = set()
    for candidate in contract["environments"]["development"]:
        candidate_id = candidate["candidate_id"]
        for seed in contract["randomization"]["training_seeds"]:
            for epoch in contract["environment_budget"]["checkpoints_after_passes"]:
                errors = []
                correct_stability = 0
                model_digests = set()
                for material_id in development_targets:
                    path = (
                        evaluation_root
                        / candidate_id
                        / f"seed_{seed}"
                        / f"epoch_{epoch:04d}"
                        / f"{material_id}.json"
                    )
                    expected_files.add(path.resolve())
                    result = load_result(path, material_id)
                    metrics = result["metrics"]
                    errors.append(metrics["frequency_mae_thz"])
                    correct_stability += int(
                        metrics["reference_stable"] == metrics["predicted_stable"]
                    )
                    model_digests.add(result["model_sha256"])
                    if epoch == max(contract["environment_budget"]["checkpoints_after_passes"]):
                        target_final[(candidate_id, material_id)][seed] = {
                            "frequency_mae_thz": metrics["frequency_mae_thz"],
                            "stability_correct": (
                                metrics["reference_stable"] == metrics["predicted_stable"]
                            ),
                        }
                if len(model_digests) != 1:
                    raise ValueError("one checkpoint produced multiple model digests")
                mean_error = sum(errors) / len(errors)
                seed_rows.append(
                    {
                        "candidate_id": candidate_id,
                        "seed": seed,
                        "pass": epoch,
                        "model_sha256": model_digests.pop(),
                        "mean_frequency_mae_thz": mean_error,
                        "utility_thz": baseline_mean - mean_error,
                        "stability_accuracy": correct_stability / len(development_targets),
                    }
                )

    observed_files = {path.resolve() for path in evaluation_root.rglob("*.json")}
    if observed_files != expected_files:
        raise ValueError("evaluation root contains missing or unexpected result files")

    grouped = defaultdict(list)
    for row in seed_rows:
        grouped[(row["candidate_id"], row["pass"])].append(row)
    mean_rows = []
    for (candidate_id, epoch), rows in sorted(grouped.items()):
        mean_rows.append(
            {
                "candidate_id": candidate_id,
                "pass": epoch,
                "mean_frequency_mae_thz": sum(row["mean_frequency_mae_thz"] for row in rows)
                / len(rows),
                "utility_thz": sum(row["utility_thz"] for row in rows) / len(rows),
                "stability_accuracy": sum(row["stability_accuracy"] for row in rows) / len(rows),
                "absolute_seed_utility_gap_thz": abs(
                    rows[0]["utility_thz"] - rows[1]["utility_thz"]
                ),
            }
        )

    target_rows = []
    for (candidate_id, material_id), by_seed in sorted(target_final.items()):
        if set(by_seed) != set(contract["randomization"]["training_seeds"]):
            raise ValueError("final target outcome is missing a frozen seed")
        outcomes = [by_seed[seed] for seed in sorted(by_seed)]
        trained_error = sum(row["frequency_mae_thz"] for row in outcomes) / len(outcomes)
        baseline = starting_by_id[material_id]
        baseline_correct = baseline["reference_stable"] == baseline["predicted_stable"]
        final_incorrect = sum(not row["stability_correct"] for row in outcomes)
        target_rows.append(
            {
                "candidate_id": candidate_id,
                "target_material_id": material_id,
                "starting_frequency_mae_thz": baseline["frequency_mae_thz"],
                "trained_frequency_mae_thz": trained_error,
                "frequency_error_ratio": trained_error / baseline["frequency_mae_thz"],
                "frequency_error_regression": (
                    trained_error > 1.05 * baseline["frequency_mae_thz"]
                ),
                "stability_regression": baseline_correct and final_incorrect > len(outcomes) / 2,
                "validity_regression": False,
            }
        )

    return {
        "artifact": "anarres_mlip_development_outcomes_v1",
        "status": "complete_development_only",
        "inputs": {
            "final_training_contract_sha256": sha256(contract_path),
            "target_roles_sha256": sha256(roles_path),
            "starting_checkpoint_targets_sha256": sha256(starting_targets_path),
        },
        "counts": {
            "environments": len(contract["environments"]["development"]),
            "training_seeds": len(contract["randomization"]["training_seeds"]),
            "checkpoints": len(contract["environment_budget"]["checkpoints_after_passes"]),
            "targets": len(development_targets),
            "evaluation_records": len(expected_files),
        },
        "baseline_mean_frequency_mae_thz": baseline_mean,
        "seed_level_curves": seed_rows,
        "seed_mean_curves": mean_rows,
        "target_regressions": target_rows,
        "prospective_boundary": {
            "prospective_candidate_training_outcomes_used": False,
            "prospective_target_outcomes_used": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--target-roles", type=Path, required=True)
    parser.add_argument("--starting-targets", type=Path, required=True)
    parser.add_argument("--evaluation-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(
        args.contract,
        args.target_roles,
        args.starting_targets,
        args.evaluation_root,
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
