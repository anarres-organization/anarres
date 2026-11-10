#!/usr/bin/env python3
"""Freeze pre-outcome selection and regression rules for the MLIP study."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_PANEL = HERE / "FINAL_COST_MATCHED_PANEL.json"
DEFAULT_ROLES = HERE / "TARGET_ROLES.json"
DEFAULT_OUTPUT = HERE / "DECISION_AND_REGRESSION_PROTOCOL.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def zscores(values: list[float]) -> list[float]:
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    scale = math.sqrt(variance)
    if scale == 0:
        raise ValueError("cannot standardize a constant coordinate")
    return [(value - mean) / scale for value in values]


def build_protocol(panel_path: Path, roles_path: Path) -> dict:
    panel = json.loads(panel_path.read_text())
    roles = json.loads(roles_path.read_text())
    candidates = panel["candidates"]

    coordinates = {
        "log_signal_density": [
            math.log(candidate["signal_density_per_atom"]) for candidate in candidates
        ],
        "effective_signal_coverage": [
            candidate["effective_signal_coverage"] for candidate in candidates
        ],
        "mean_target_affinity": [candidate["mean_target_affinity"] for candidate in candidates],
    }
    standardized = {name: zscores(values) for name, values in coordinates.items()}

    ranked = []
    for index, candidate in enumerate(candidates):
        score = sum(values[index] for values in standardized.values()) / len(standardized)
        ranked.append(
            {
                "candidate_id": candidate["candidate_id"],
                "role": candidate["role"],
                "score": score,
                "coordinates": {name: coordinates[name][index] for name in coordinates},
                "standardized_coordinates": {
                    name: standardized[name][index] for name in standardized
                },
            }
        )
    ranked.sort(key=lambda item: (-item["score"], item["candidate_id"]))
    for rank, item in enumerate(ranked, start=1):
        item["rank"] = rank

    return {
        "artifact": "anarres_mlip_decision_and_regression_protocol_v1",
        "status": "frozen_before_candidate_training_outcomes",
        "inputs": {
            "candidate_panel": {
                "path": panel_path.name,
                "sha256": sha256(panel_path),
                "status": panel["status"],
            },
            "target_roles": {
                "path": roles_path.name,
                "sha256": sha256(roles_path),
                "role_hashes": roles["role_hashes"],
            },
        },
        "literature_derived_baseline": {
            "name": "equal_weight_signal_coverage_affinity",
            "purpose": (
                "A fixed, outcome-blind comparator derived from the pooled retrospective bridge; "
                "it is not the development-fitted prospective predictor."
            ),
            "formula": (
                "mean(z(log(signal_density_per_atom)), "
                "z(effective_signal_coverage), z(mean_target_affinity))"
            ),
            "standardization_population": "all 16 frozen candidate environments",
            "uses_candidate_training_outcomes": False,
            "ranking": ranked,
        },
        "prospective_environment_selection": {
            "development_environments": 12,
            "prospective_environments": 4,
            "development_targets": 25,
            "prospective_targets": 50,
            "sequence": [
                "train and score the 12 development environments",
                "fit compact predictors using complete-environment holdouts",
                "select one predictor without opening prospective-environment outcomes",
                "serialize prospective predictions, rankings, uncertainty, and artifact hashes",
                "train and score the four prospective environments",
            ],
            "candidate_predictors": [
                "signal_density_only",
                "effective_coverage_only",
                "target_affinity_only",
                "signal_coverage_affinity",
            ],
            "decision_baselines": [
                "equal_weight_signal_coverage_affinity",
                "fixed_source_family_selected_inside_each_training_fold",
                "fixed_selection_rule_selected_inside_each_training_fold",
                "hash_uniform",
                "random_choice_expectation",
            ],
            "primary_metrics": [
                "whole_curve_phonon_frequency_error",
                "pairwise_environment_ordering",
                "best_environment_decision",
                "allocation_regret",
            ],
            "guardrails": [
                "environment membership and target roles remain fixed",
                "all coordinates are measured before candidate post-training",
                "complete environments, not checkpoints or targets, define selection holdouts",
                "curve prediction and allocation decisions are reported separately",
                "measurement and reference-label cost are reported alongside training cost",
            ],
        },
        "target_regression_prediction": {
            "question": (
                "Which target materials become worse than the common starting checkpoint after "
                "training on an environment, even when aggregate phonon performance improves?"
            ),
            "unit": "target_material_by_environment_at_a_prespecified_checkpoint",
            "primary_endpoint": {
                "name": "frequency_error_regression",
                "definition": (
                    "The seed-mean commensurate-phonon frequency MAE exceeds 1.05 times the "
                    "starting-checkpoint MAE for the same material."
                ),
                "rationale": (
                    "The five-percent boundary matches the practical-equivalence band fixed for "
                    "starting-checkpoint qualification."
                ),
            },
            "secondary_endpoints": [
                {
                    "name": "stability_regression",
                    "definition": (
                        "The starting checkpoint classifies dynamical stability correctly and a "
                        "majority of prespecified training seeds classify it incorrectly."
                    ),
                },
                {
                    "name": "validity_regression",
                    "definition": (
                        "The starting checkpoint completes the released phonon workflow and a "
                        "majority of prespecified training seeds fail it."
                    ),
                },
            ],
            "pretraining_features": [
                "starting_checkpoint_target_error_and_stability_margin",
                "candidate_signal_density",
                "candidate_effective_coverage",
                "candidate_target_affinity",
                "target_element_and_structure_descriptors",
                "target_specific_chemical_support_in_the_candidate",
                "target_specific_nearest_neighbor_affinity_to_the_candidate",
                "source_regime_and_selection_rule",
            ],
            "development_evaluation": [
                "leave_one_environment_out",
                "leave_one_target_material_out",
                "leave_one_chemical_system_out",
            ],
            "prospective_test": (
                "Freeze target-level probabilities on all 50 prospective materials for each of "
                "the four prospective environments before opening their outcomes."
            ),
            "metrics": [
                "roc_auc",
                "average_precision",
                "brier_score",
                "recall_in_the_top_risk_20_percent",
                "source_and_environment_macro_averages",
            ],
            "negative_controls": [
                "starting_checkpoint_error_only",
                "candidate_identity_only",
                "permuted_regression_labels",
            ],
        },
        "outcome_boundary": {
            "candidate_training_outcomes_used": False,
            "development_target_outcomes_used": False,
            "prospective_target_outcomes_used": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--roles", type=Path, default=DEFAULT_ROLES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    protocol = build_protocol(args.panel, args.roles)
    args.output.write_text(json.dumps(protocol, indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
