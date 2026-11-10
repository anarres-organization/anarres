#!/usr/bin/env python3
"""Score frozen materials utility and regression predictions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from fit_aggregate_utility import decision_metrics
from fit_target_regressions import macro_metrics, metrics


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(
    authorization_path: Path,
    aggregate_fit_path: Path,
    regression_fit_path: Path,
    outcomes_path: Path,
) -> dict:
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    aggregate = json.loads(aggregate_fit_path.read_text(encoding="utf-8"))
    regressions = json.loads(regression_fit_path.read_text(encoding="utf-8"))
    outcomes = json.loads(outcomes_path.read_text(encoding="utf-8"))
    if authorization["aggregate_utility_fit_sha256"] != sha256(aggregate_fit_path):
        raise ValueError("authorization does not bind the aggregate forecast")
    if authorization["target_regression_fit_sha256"] != sha256(regression_fit_path):
        raise ValueError("authorization does not bind the regression forecast")
    if not all(outcomes["prospective_boundary"].values()):
        raise ValueError("prospective outcomes have not opened both protected boundaries")

    forecast_points = {
        (environment["candidate_id"], point["pass"]): point
        for environment in aggregate["prospective_forecast"]
        for point in environment["curve"]
    }
    observed_points = {
        (row["candidate_id"], row["pass"]): row for row in outcomes["seed_mean_curves"]
    }
    if forecast_points.keys() != observed_points.keys():
        raise ValueError("aggregate forecast and prospective surface do not match")
    curve_rows = []
    covered = 0
    for key in sorted(forecast_points):
        forecast = forecast_points[key]
        observed = observed_points[key]
        covered += int(
            abs(forecast["predicted_utility_thz"] - observed["utility_thz"])
            <= forecast["empirical_half_width_thz"]
        )
        curve_rows.append(
            {
                "candidate_id": key[0],
                "pass": key[1],
                "predicted": forecast["predicted_utility_thz"],
                "observed": observed["utility_thz"],
            }
        )
    aggregate_metrics = decision_metrics(curve_rows)
    aggregate_metrics["empirical_envelope_coverage"] = covered / len(curve_rows)
    aggregate_metrics["covered_points"] = covered
    aggregate_metrics["curve_points"] = len(curve_rows)

    baseline_scores = []
    for name in sorted({row["name"] for row in authorization["baseline_decisions"]}):
        decisions = [row for row in authorization["baseline_decisions"] if row["name"] == name]
        if any(not row["selected_candidates"] for row in decisions):
            baseline_scores.append({"name": name, "applicable": False})
            continue
        regrets = []
        wins = 0
        for decision in decisions:
            epoch_rows = [row for row in curve_rows if row["pass"] == decision["pass"]]
            best = max(row["observed"] for row in epoch_rows)
            selected = [
                row["observed"]
                for row in epoch_rows
                if row["candidate_id"] in decision["selected_candidates"]
            ]
            regrets.append(best - float(np.mean(selected)))
            winners = {row["candidate_id"] for row in epoch_rows if row["observed"] == best}
            wins += int(bool(winners & set(decision["selected_candidates"])))
        baseline_scores.append(
            {
                "name": name,
                "applicable": True,
                "best_environment_decisions": wins,
                "decision_count": len(decisions),
                "mean_allocation_regret_thz": float(np.mean(regrets)),
            }
        )

    predicted_regressions = {
        (row["candidate_id"], row["target_material_id"]): row
        for row in regressions["prospective_predictions"]
    }
    observed_regressions = {
        (row["candidate_id"], row["target_material_id"]): row
        for row in outcomes["target_regressions"]
    }
    if predicted_regressions.keys() != observed_regressions.keys():
        raise ValueError("target forecast and prospective regression panel do not match")
    keys = sorted(predicted_regressions)
    labels = np.asarray(
        [float(observed_regressions[key]["frequency_error_regression"]) for key in keys]
    )
    probabilities = np.asarray(
        [predicted_regressions[key]["frequency_error_regression_probability"] for key in keys]
    )
    environment_groups = [key[0] for key in keys]
    source_groups = [key[0].split("__", 1)[0] for key in keys]
    regression_metrics = metrics(labels, probabilities)
    regression_metrics["environment_macro"] = macro_metrics(
        labels, probabilities, environment_groups
    )
    regression_metrics["source_family_macro"] = macro_metrics(labels, probabilities, source_groups)
    regression_metrics["stability_regressions"] = sum(
        row["stability_regression"] for row in observed_regressions.values()
    )
    regression_metrics["validity_regressions"] = sum(
        row["validity_regression"] for row in observed_regressions.values()
    )

    return {
        "artifact": "anarres_mlip_prospective_prediction_score_v1",
        "status": "prospective_test_scored",
        "inputs": {
            "prospective_authorization_sha256": sha256(authorization_path),
            "aggregate_utility_fit_sha256": sha256(aggregate_fit_path),
            "target_regression_fit_sha256": sha256(regression_fit_path),
            "prospective_outcomes_sha256": sha256(outcomes_path),
        },
        "aggregate_utility": aggregate_metrics,
        "allocation_baselines": baseline_scores,
        "target_regressions": regression_metrics,
        "counts": outcomes["counts"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--aggregate-fit", type=Path, required=True)
    parser.add_argument("--regression-fit", type=Path, required=True)
    parser.add_argument("--prospective-outcomes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = score(
        args.authorization,
        args.aggregate_fit,
        args.regression_fit,
        args.prospective_outcomes,
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
