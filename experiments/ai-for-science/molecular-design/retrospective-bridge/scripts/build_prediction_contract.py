#!/usr/bin/env python3
"""Build the normalized molecular decision and prediction contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def compact_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    """Retain aggregate decision metrics without duplicating fold-level records."""
    excluded = {"selections", "folds", "chosen_hyperparameters_by_target"}
    return {key: value for key, value in payload.items() if key not in excluded}


def build(data: Path) -> dict[str, Any]:
    antoniuk = load(data / "antoniuk_active_learning_bridge_v1.json")
    invirtuo = load(data / "invirtuo_replay_bridge_v1.json")
    saturn = load(data / "saturn_bridge_v1.json")
    tsmiles = load(data / "tsmiles_jnk3_bridge_v1.json")
    pmo = load(data / "pmo_decision_ladder_v1.json")
    vantilborg = load(data / "vantilborg_active_learning_bridge_v1.json")
    reisman = load(data / "reisman_regioselectivity_bridge_v1.json")
    explainable_al = load(data / "explainable_active_learning_bridge_v1.json")

    return {
        "schema_version": "anarres.molecular.prediction_contract.v1",
        "status": "retrospective_contract_with_released_prospective_test",
        "normalization": {
            "decision_panel": (
                "One source, target context, downstream contract, endpoint, and budget with "
                "only the candidate acquisition or environment choice varying."
            ),
            "outcome": (
                "Orient native outcomes so larger is better, then min-max normalize only "
                "within a matched decision panel. A tied panel receives utility 0.5."
            ),
            "prediction_inputs": (
                "Standardize continuous inputs inside each training fold or derive ranks from "
                "candidate measurements without using held-out outcomes."
            ),
            "evaluation": (
                "Hold out complete scientific contexts and report pairwise ordering, mean "
                "panel-normalized regret, and top-choice credit with half credit for ties."
            ),
            "baselines": [
                "uninformed tie",
                "training-fold-selected fixed candidate",
                "simple scientific rule",
            ],
            "cost": (
                "Keep measurement, oracle, training, and evaluation cost separate. A panel is "
                "cost-matched only when the released intervention supports that claim."
            ),
        },
        "prediction_audits": {
            "pmo_temporal": {
                "source_object": "PMO",
                "panels": pmo["support"]["tasks"],
                "candidate_arms": pmo["support"]["method_task_pairs"],
                "holdout_unit": "one complete oracle task",
                "normalized_outcome": "final AUC Top-10 within oracle task",
                "decision_information": (
                    "training-fold method prior plus task-specific AUC observed through the "
                    "charged pilot budget"
                ),
                "measurement_timing": "early downstream optimization",
                "cost_contract": pmo["evaluation"]["cost_contract"],
                "pretraining_profile_input": False,
                "primary_metrics": compact_metrics(
                    pmo["budget_results"][0]["metrics"]["prior_plus_pilot_auc"]
                ),
            },
            "vantilborg_cross_library": {
                "source_object": "van Tilborg and Grisoni",
                "panels": vantilborg["support"]["contexts"],
                "candidate_arms": vantilborg["support"]["condition_records"],
                "holdout_unit": "one complete molecular library",
                "normalized_outcome": "terminal hits within library and architecture",
                "decision_information": (
                    "acquisition identity, architecture, and measurements from the initial "
                    "labeled batch"
                ),
                "measurement_timing": "before iterative active-learning acquisition",
                "cost_contract": "common acquisition-cycle contract within each panel",
                "pretraining_profile_input": False,
                "primary_metrics": compact_metrics(
                    vantilborg["leave_one_dataset_out"]["method_by_architecture"]
                ),
                "graph_measurement_sensitivity": compact_metrics(
                    vantilborg["leave_one_dataset_out"]["graph"]
                ),
            },
            "reisman_cross_target": {
                "source_object": "Schleinitz et al.",
                "panels": reisman["support"]["targets"],
                "candidate_arms": reisman["support"]["conditions"],
                "holdout_unit": "one complete target molecule",
                "normalized_outcome": "negative stable-top-1 index within target",
                "decision_information": (
                    "target Morgan fingerprint and acquisition outcomes from other targets"
                ),
                "measurement_timing": "before opening the held-out target outcomes",
                "cost_contract": "common simulated acquisition contract within each target",
                "pretraining_profile_input": False,
                "primary_metrics": compact_metrics(
                    reisman["stable_top1_decision_audit"]["structural_nearest_target"]
                ),
                "nested_similarity_sensitivity": compact_metrics(
                    reisman["stable_top1_decision_audit"]["nested_similarity_weighted"]
                ),
            },
            "explainable_al_cross_target": {
                "source_object": "Srivastava et al.",
                "panels": explainable_al["support"]["decision_panels"],
                "candidate_arms": explainable_al["support"]["condition_records"],
                "holdout_unit": "one complete binding-affinity dataset",
                "normalized_outcome": (
                    "three-seed endpoint top-2%-recall within dataset, fingerprint, and kernel"
                ),
                "decision_information": (
                    "acquisition-schedule outcomes from other datasets, with the transfer view "
                    "selected using only inner training-dataset folds"
                ),
                "measurement_timing": "before opening the held-out dataset outcomes",
                "cost_contract": "360 acquired compounds for every candidate within each panel",
                "pretraining_profile_input": False,
                "primary_metrics": compact_metrics(
                    explainable_al["leave_one_dataset_out"]["nested_view_selection"]
                ),
                "kernel_matched_sensitivity": compact_metrics(
                    explainable_al["leave_one_dataset_out"]["kernel_matched"]
                ),
                "dataset_clustered_uncertainty": explainable_al["dataset_clustered_uncertainty"],
            },
        },
        "supporting_objects": {
            "antoniuk_active_learning": {
                "support": antoniuk["support"],
                "role": "mechanism evidence",
                "predictor_eligibility": "excluded: preceding acquisition cost is unmatched",
            },
            "invirtuogen_replay": {
                "support": invirtuo["support"],
                "role": "matched intervention evidence",
                "predictor_eligibility": (
                    "excluded: no released outcome-blind task coordinates distinguish candidates"
                ),
            },
            "saturn": {
                "support": saturn["support"],
                "role": "architecture and augmentation compatibility evidence",
                "predictor_eligibility": (
                    "excluded: candidate changes include model or method contracts"
                ),
            },
            "tsmiles": {
                "support": tsmiles["support"],
                "role": "representation and training-duration evidence",
                "predictor_eligibility": (
                    "excluded: representation, augmentation, and exposure change together"
                ),
            },
        },
        "prospective_boundary": {
            "claim_bearing_test": "RxnFlow reaction-environment selection",
            "status": "released",
            "result": (
                "experiments/ai-for-science/molecular-design/"
                "reaction-environment-selection/PROSPECTIVE_RESULTS.json"
            ),
            "interpretation": (
                "The frozen point forecast gets the two-bank ordering right at all three "
                "budgets, while the prespecified uncertainty rule abstains at all three."
            ),
            "explore_template": (
                "The pinned RxnFlow explore template defines the synthesis action space. It is "
                "a source-construction asset, not a predictor coordinate or downstream outcome."
            ),
            "admission_rule": (
                "Use explore-derived candidates only after independent probe measurements are "
                "normalized under the frozen prospective contract."
            ),
        },
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
