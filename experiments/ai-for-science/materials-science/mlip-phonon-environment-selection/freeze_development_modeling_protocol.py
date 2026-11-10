#!/usr/bin/env python3
"""Freeze development-model selection before opening development outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(
    decision_protocol: Path,
    training_contract: Path,
    starting_targets: Path,
    regression_features: Path,
) -> dict:
    decision = json.loads(decision_protocol.read_text(encoding="utf-8"))
    contract = json.loads(training_contract.read_text(encoding="utf-8"))
    features = json.loads(regression_features.read_text(encoding="utf-8"))
    if any(decision["outcome_boundary"].values()):
        raise ValueError("decision protocol already crosses the outcome boundary")
    if any(contract["outcome_boundary"].values()):
        raise ValueError("training contract already crosses the outcome boundary")
    if any(features["outcome_boundary"].values()):
        raise ValueError("regression features cross the outcome boundary")
    return {
        "artifact": "anarres_mlip_development_modeling_protocol_v1",
        "status": "frozen_before_development_outcome_analysis",
        "inputs": {
            "decision_and_regression_protocol_sha256": sha256(decision_protocol),
            "final_training_contract_sha256": sha256(training_contract),
            "starting_checkpoint_targets_sha256": sha256(starting_targets),
            "target_regression_features_sha256": sha256(regression_features),
        },
        "aggregate_utility": {
            "unit": (
                "environment by pass, averaged across the two frozen training seeds and 25 "
                "development targets"
            ),
            "definition": (
                "Starting-checkpoint mean frequency MAE minus trained-checkpoint mean frequency "
                "MAE in THz; positive values indicate improvement."
            ),
            "budget": "completed equal-cost passes over one 50000-atom, 2100000-edge environment",
            "candidate_predictors": {
                "signal_density_only": ["log_signal_density"],
                "effective_coverage_only": ["effective_signal_coverage"],
                "target_affinity_only": ["mean_target_affinity"],
                "signal_coverage_affinity": [
                    "log_signal_density",
                    "effective_signal_coverage",
                    "mean_target_affinity",
                ],
            },
            "response_surface": (
                "Four pass-specific intercepts plus s(pass) times standardized environment "
                "coordinates, where s(pass)=pass/(pass+1)."
            ),
            "standardization": (
                "Fit mean and population standard deviation inside each training fold."
            ),
            "cross_validation": (
                "Leave one complete development environment out, preserving both seeds and all "
                "checkpoints inside the held-out unit."
            ),
            "selection_rule": (
                "Select the candidate with the lowest leave-one-environment-out curve RMSE. "
                "Break exact ties by higher pairwise rank accuracy, then lower allocation regret, "
                "then fewer coordinates."
            ),
            "metrics": [
                "curve_rmse_thz",
                "pairwise_environment_ordering",
                "best_environment_decision",
                "allocation_regret_thz",
            ],
            "decision_baselines": decision["prospective_environment_selection"][
                "decision_baselines"
            ],
            "uncertainty": (
                "Calibrate a curve-level empirical envelope from each held-out environment's "
                "maximum absolute residual and report observed two-seed differences separately."
            ),
        },
        "target_regressions": {
            "primary_label": decision["target_regression_prediction"]["primary_endpoint"],
            "secondary_labels": decision["target_regression_prediction"]["secondary_endpoints"],
            "checkpoint": "pass 4",
            "seed_aggregation": (
                "Two-seed mean for frequency error; majority rule for binary stability and "
                "validity endpoints."
            ),
            "candidate_models": {
                "starting_error_only": ["log_starting_frequency_mae"],
                "environment_only": [
                    "log_signal_density",
                    "effective_signal_coverage",
                    "mean_target_affinity",
                ],
                "starting_plus_support": [
                    "log_starting_frequency_mae",
                    "starting_predicted_stability_margin_kelvin",
                    "element_distribution_overlap",
                    "record_fraction_containing_all_target_elements",
                    "top_five_percent_element_set_jaccard",
                ],
                "full_numeric": [
                    "log_starting_frequency_mae",
                    "starting_predicted_stability_margin_kelvin",
                    "target_element_count",
                    "target_unitcell_atoms",
                    "log_signal_density",
                    "effective_signal_coverage",
                    "mean_target_affinity",
                    "element_distribution_overlap",
                    "record_fraction_containing_all_target_elements",
                    "top_five_percent_element_set_jaccard",
                ],
                "full_with_environment_labels": [
                    "full_numeric",
                    "one_hot_source_family",
                    "one_hot_selection_rule",
                ],
            },
            "estimator": (
                "L2-regularized logistic regression with penalty strengths 0.1, 1, and 10 "
                "selected inside each outer training fold."
            ),
            "primary_cross_validation": "Leave one complete development environment out.",
            "secondary_cross_validation": [
                "leave one target material out",
                "leave one target element set out",
            ],
            "selection_rule": (
                "Select the candidate with the lowest leave-one-environment-out Brier score. "
                "Break exact ties by higher average precision, then higher ROC AUC, then fewer "
                "features."
            ),
            "metrics": decision["target_regression_prediction"]["metrics"],
            "negative_controls": decision["target_regression_prediction"]["negative_controls"],
        },
        "prospective_freeze": {
            "aggregate": (
                "Serialize four curves, rankings, uncertainty, and the selected environment at "
                "every pass."
            ),
            "regressions": (
                "Serialize one probability for each of 200 prospective environment-target pairs "
                "before prospective training."
            ),
            "authorization": (
                "Prospective training requires a separate artifact that binds this protocol, "
                "selected models, predictions, and the final training contract."
            ),
        },
        "outcome_boundary": {
            "development_candidate_training_outcomes_used": False,
            "prospective_candidate_training_outcomes_used": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision-protocol", type=Path, required=True)
    parser.add_argument("--training-contract", type=Path, required=True)
    parser.add_argument("--starting-targets", type=Path, required=True)
    parser.add_argument("--regression-features", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = freeze(
        args.decision_protocol,
        args.training_contract,
        args.starting_targets,
        args.regression_features,
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
