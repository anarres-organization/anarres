#!/usr/bin/env python3
"""Audit the scored materials prospective test without changing its forecast."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

COORDINATES = (
    "signal_density_per_atom",
    "effective_signal_coverage",
    "mean_target_affinity",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_audit(
    panel_path: Path,
    aggregate_fit_path: Path,
    regression_fit_path: Path,
    outcomes_path: Path,
    score_path: Path,
) -> dict[str, Any]:
    panel = read(panel_path)
    aggregate = read(aggregate_fit_path)
    regressions = read(regression_fit_path)
    outcomes = read(outcomes_path)
    score = read(score_path)

    expected = score.get("inputs", {})
    observed_hashes = {
        "aggregate_utility_fit_sha256": sha256(aggregate_fit_path),
        "target_regression_fit_sha256": sha256(regression_fit_path),
        "prospective_outcomes_sha256": sha256(outcomes_path),
    }
    for key, value in observed_hashes.items():
        if expected.get(key) != value:
            raise ValueError(f"prospective score does not bind {key}")

    candidates = {row["candidate_id"]: row for row in panel["candidates"]}
    development = [row for row in candidates.values() if row["role"] == "development"]
    prospective = [row for row in candidates.values() if row["role"] == "prospective"]
    if len(development) != 12 or len(prospective) != 4:
        raise ValueError("expected 12 development and four prospective candidates")

    support = {
        coordinate: {
            "minimum": min(float(row[coordinate]) for row in development),
            "maximum": max(float(row[coordinate]) for row in development),
        }
        for coordinate in COORDINATES
    }

    selected = aggregate["selected_model"]
    selected_features = selected["features"]
    if selected_features != ["log_signal_density"]:
        raise ValueError("support audit expects the frozen signal-density model")
    mean = float(selected["fit"]["means"]["log_signal_density"])
    scale = float(selected["fit"]["scales"]["log_signal_density"])

    support_rows = []
    for row in sorted(prospective, key=lambda item: item["candidate_id"]):
        density = float(row["signal_density_per_atom"])
        density_support = support["signal_density_per_atom"]
        inside = density_support["minimum"] <= density <= density_support["maximum"]
        support_rows.append(
            {
                "candidate_id": row["candidate_id"],
                "selected_model_coordinate": "log_signal_density",
                "signal_density_per_atom": density,
                "standardized_log_signal_density": (math.log(density) - mean) / scale,
                "inside_development_signal_density_range": inside,
                "relative_gap_below_development_minimum": (
                    max(0.0, density_support["minimum"] - density) / density_support["minimum"]
                ),
            }
        )

    forecasts = {
        row["candidate_id"]: {
            int(point["pass"]): float(point["predicted_utility_thz"]) for point in row["curve"]
        }
        for row in aggregate["prospective_forecast"]
    }
    observed = {
        (row["candidate_id"], int(row["pass"])): float(row["utility_thz"])
        for row in outcomes["seed_mean_curves"]
    }
    if set(forecasts) != {row["candidate_id"] for row in prospective}:
        raise ValueError("forecast does not cover the prospective candidate panel")

    curve_rows = []
    squared_error_by_candidate: dict[str, float] = {}
    for candidate_id in sorted(forecasts):
        points = []
        squared_error = 0.0
        for training_pass in sorted(forecasts[candidate_id]):
            prediction = forecasts[candidate_id][training_pass]
            utility = observed[(candidate_id, training_pass)]
            residual = utility - prediction
            squared_error += residual**2
            points.append(
                {
                    "pass": training_pass,
                    "predicted_utility_thz": prediction,
                    "observed_utility_thz": utility,
                    "residual_thz": residual,
                }
            )
        squared_error_by_candidate[candidate_id] = squared_error
        curve_rows.append({"candidate_id": candidate_id, "curve": points})

    total_squared_error = sum(squared_error_by_candidate.values())
    error_attribution = [
        {
            "candidate_id": candidate_id,
            "share_of_total_squared_error": value / total_squared_error,
        }
        for candidate_id, value in sorted(
            squared_error_by_candidate.items(), key=lambda item: (-item[1], item[0])
        )
    ]

    inside_ids = {
        row["candidate_id"]
        for row in support_rows
        if row["inside_development_signal_density_range"]
    }
    decisions = []
    for training_pass in sorted(next(iter(forecasts.values()))):
        predicted_best = max(forecasts, key=lambda cid: forecasts[cid][training_pass])
        observed_best = max(forecasts, key=lambda cid: observed[(cid, training_pass)])
        supported_best = max(inside_ids, key=lambda cid: forecasts[cid][training_pass])
        decisions.append(
            {
                "pass": training_pass,
                "frozen_predicted_best": predicted_best,
                "observed_best": observed_best,
                "predicted_best_inside_development_support": predicted_best in inside_ids,
                "post_hoc_support_restricted_best": supported_best,
                "post_hoc_support_restricted_regret_thz": (
                    observed[(observed_best, training_pass)]
                    - observed[(supported_best, training_pass)]
                ),
            }
        )

    probabilities = {
        (row["candidate_id"], row["target_material_id"]): float(
            row["frequency_error_regression_probability"]
        )
        for row in regressions["prospective_predictions"]
    }
    labels = {
        (row["candidate_id"], row["target_material_id"]): bool(row["frequency_error_regression"])
        for row in outcomes["target_regressions"]
    }
    if probabilities.keys() != labels.keys():
        raise ValueError("regression forecast and outcome panels do not match")

    regression_groups = []
    for candidate_id in sorted(forecasts):
        keys = [key for key in labels if key[0] == candidate_id]
        regression_groups.append(
            {
                "candidate_id": candidate_id,
                "targets": len(keys),
                "observed_regressions": sum(labels[key] for key in keys),
                "observed_regression_rate": sum(labels[key] for key in keys) / len(keys),
                "mean_predicted_probability": sum(probabilities[key] for key in keys) / len(keys),
            }
        )

    return {
        "artifact": "anarres_mlip_post_prospective_audit_v1",
        "status": "exploratory_post_prospective_audit",
        "evidence_boundary": {
            "frozen_forecast_modified": False,
            "prospective_score_modified": False,
            "support_guard_prespecified": False,
            "interpretation": (
                "Support-restricted decisions are retrospective sensitivities. "
                "They are not prospective results."
            ),
        },
        "inputs": {
            "candidate_panel_sha256": sha256(panel_path),
            **observed_hashes,
            "prospective_prediction_score_sha256": sha256(score_path),
        },
        "selected_model": {
            "name": selected["name"],
            "features": selected_features,
            "coefficient_by_pass": {
                str(training_pass): float(coefficient)
                for training_pass, coefficient in zip(
                    selected["fit"]["passes"],
                    selected["fit"]["coefficients"][1:],
                    strict=True,
                )
            },
        },
        "development_coordinate_support": support,
        "prospective_support": support_rows,
        "prospective_score": score,
        "curve_comparison": curve_rows,
        "error_attribution": error_attribution,
        "decision_audit": {
            "abstention_rule": (
                "Abstain when the frozen predicted winner lies outside the development "
                "range of any selected model coordinate."
            ),
            "would_abstain_at_all_budgets": all(
                not row["predicted_best_inside_development_support"] for row in decisions
            ),
            "decisions": decisions,
        },
        "target_regression_by_environment": regression_groups,
        "observed_boundary": {
            "all_prospective_environment_budget_utilities_negative": all(
                value < 0 for value in observed.values()
            ),
            "selected_environment_worst_at_all_budgets": all(
                row["frozen_predicted_best"]
                == min(forecasts, key=lambda cid: observed[(cid, row["pass"])])
                for row in decisions
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-panel", type=Path, required=True)
    parser.add_argument("--aggregate-fit", type=Path, required=True)
    parser.add_argument("--regression-fit", type=Path, required=True)
    parser.add_argument("--prospective-outcomes", type=Path, required=True)
    parser.add_argument("--prospective-score", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_audit(
        args.candidate_panel,
        args.aggregate_fit,
        args.regression_fit,
        args.prospective_outcomes,
        args.prospective_score,
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
