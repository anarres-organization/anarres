#!/usr/bin/env python3
"""Bind frozen prospective predictions before prospective candidate training."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(
    training_contract_path: Path,
    modeling_protocol_path: Path,
    aggregate_fit_path: Path,
    regression_fit_path: Path,
) -> dict:
    aggregate = json.loads(aggregate_fit_path.read_text(encoding="utf-8"))
    regressions = json.loads(regression_fit_path.read_text(encoding="utf-8"))
    if any(aggregate["prospective_boundary"].values()):
        raise ValueError("aggregate fit crosses the prospective boundary")
    if any(regressions["prospective_boundary"].values()):
        raise ValueError("regression fit crosses the prospective boundary")
    curves = aggregate["prospective_forecast"]
    passes = sorted({point["pass"] for item in curves for point in item["curve"]})
    decisions = []
    for epoch in passes:
        ranking = sorted(
            (
                {
                    "candidate_id": item["candidate_id"],
                    "predicted_utility_thz": next(
                        point["predicted_utility_thz"]
                        for point in item["curve"]
                        if point["pass"] == epoch
                    ),
                }
                for item in curves
            ),
            key=lambda item: (item["predicted_utility_thz"], item["candidate_id"]),
            reverse=True,
        )
        decisions.append(
            {
                "pass": epoch,
                "selected_candidate": ranking[0]["candidate_id"],
                "ranking": [item["candidate_id"] for item in ranking],
                "predicted_margin_thz": (
                    ranking[0]["predicted_utility_thz"] - ranking[1]["predicted_utility_thz"]
                ),
            }
        )
    return {
        "artifact": "anarres_mlip_prospective_training_authorization_v1",
        "status": "prospective_predictions_frozen",
        "final_training_contract_sha256": sha256(training_contract_path),
        "development_modeling_protocol_sha256": sha256(modeling_protocol_path),
        "aggregate_utility_fit_sha256": sha256(aggregate_fit_path),
        "target_regression_fit_sha256": sha256(regression_fit_path),
        "aggregate_model": aggregate["selected_model"]["name"],
        "regression_model": regressions["selected_model"]["name"],
        "decisions": decisions,
        "baseline_decisions": aggregate["prospective_baseline_decisions"],
        "forecast_counts": {
            "environment_curves": len(curves),
            "environment_budget_points": sum(len(item["curve"]) for item in curves),
            "target_regression_probabilities": len(regressions["prospective_predictions"]),
        },
        "outcome_boundary": {
            "prospective_candidate_training_outcomes_used": False,
            "prospective_target_outcomes_used": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--training-contract", type=Path, required=True)
    parser.add_argument("--modeling-protocol", type=Path, required=True)
    parser.add_argument("--aggregate-fit", type=Path, required=True)
    parser.add_argument("--regression-fit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = freeze(
        args.training_contract,
        args.modeling_protocol,
        args.aggregate_fit,
        args.regression_fit,
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
