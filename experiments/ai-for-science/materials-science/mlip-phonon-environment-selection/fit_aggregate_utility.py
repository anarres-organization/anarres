#!/usr/bin/env python3
"""Select and fit frozen aggregate materials utility predictors."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate_coordinates(candidate: dict) -> dict[str, float]:
    return {
        "log_signal_density": math.log(candidate["signal_density_per_atom"]),
        "effective_signal_coverage": candidate["effective_signal_coverage"],
        "mean_target_affinity": candidate["mean_target_affinity"],
    }


def fit_surface(
    rows: list[dict], candidates: dict[str, dict], features: list[str], passes: list[int]
) -> dict:
    train_ids = sorted({row["candidate_id"] for row in rows})
    means = {
        feature: float(
            np.mean([candidate_coordinates(candidates[item])[feature] for item in train_ids])
        )
        for feature in features
    }
    scales = {
        feature: float(
            np.std([candidate_coordinates(candidates[item])[feature] for item in train_ids])
        )
        for feature in features
    }
    if any(scale == 0.0 for scale in scales.values()):
        raise ValueError("training fold contains a constant predictor")

    design = []
    response = []
    for row in rows:
        budget = [float(row["pass"] == value) for value in passes]
        saturation = row["pass"] / (row["pass"] + 1.0)
        coordinates = candidate_coordinates(candidates[row["candidate_id"]])
        environment = [
            saturation * (coordinates[feature] - means[feature]) / scales[feature]
            for feature in features
        ]
        design.append(budget + environment)
        response.append(row["utility_thz"])
    coefficients, _, rank, _ = np.linalg.lstsq(np.asarray(design), np.asarray(response), rcond=None)
    if rank != len(passes) + len(features):
        raise ValueError("aggregate response surface is rank deficient")
    return {
        "passes": passes,
        "features": features,
        "means": means,
        "scales": scales,
        "coefficients": coefficients.tolist(),
    }


def predict_surface(model: dict, candidate: dict, epoch: int) -> float:
    budget = [float(epoch == value) for value in model["passes"]]
    saturation = epoch / (epoch + 1.0)
    coordinates = candidate_coordinates(candidate)
    environment = [
        saturation * (coordinates[feature] - model["means"][feature]) / model["scales"][feature]
        for feature in model["features"]
    ]
    return float(np.dot(model["coefficients"], budget + environment))


def decision_metrics(predictions: list[dict]) -> dict:
    squared = [(row["predicted"] - row["observed"]) ** 2 for row in predictions]
    rank_correct = 0.0
    rank_total = 0
    regrets = []
    wins = 0
    for epoch in sorted({row["pass"] for row in predictions}):
        rows = sorted(
            (row for row in predictions if row["pass"] == epoch),
            key=lambda row: row["candidate_id"],
        )
        for left_index, left in enumerate(rows):
            for right in rows[left_index + 1 :]:
                predicted_difference = left["predicted"] - right["predicted"]
                observed_difference = left["observed"] - right["observed"]
                if predicted_difference == 0.0 or observed_difference == 0.0:
                    rank_correct += 0.5
                elif predicted_difference * observed_difference > 0.0:
                    rank_correct += 1.0
                rank_total += 1
        best_predicted_value = max(row["predicted"] for row in rows)
        predicted_best = [row for row in rows if row["predicted"] == best_predicted_value]
        observed_best = max(rows, key=lambda row: (row["observed"], row["candidate_id"]))
        selected_observed = sum(row["observed"] for row in predicted_best) / len(predicted_best)
        regrets.append(observed_best["observed"] - selected_observed)
        wins += int(
            any(row["candidate_id"] == observed_best["candidate_id"] for row in predicted_best)
        )
    return {
        "curve_rmse_thz": math.sqrt(sum(squared) / len(squared)),
        "pairwise_rank_accuracy": rank_correct / rank_total,
        "best_environment_decisions": wins,
        "decision_count": len(regrets),
        "mean_allocation_regret_thz": sum(regrets) / len(regrets),
    }


def allocation_baselines(
    rows: list[dict], candidates: dict[str, dict], passes: list[int]
) -> list[dict]:
    candidate_ids = sorted({row["candidate_id"] for row in rows})
    predictions = {
        name: []
        for name in (
            "equal_weight_signal_coverage_affinity",
            "fixed_source_family_selected_inside_each_training_fold",
            "fixed_selection_rule_selected_inside_each_training_fold",
            "hash_uniform",
        )
    }
    coordinate_names = ["log_signal_density", "effective_signal_coverage", "mean_target_affinity"]
    for heldout in candidate_ids:
        training_ids = [candidate_id for candidate_id in candidate_ids if candidate_id != heldout]
        coordinate_rows = {
            candidate_id: candidate_coordinates(candidates[candidate_id])
            for candidate_id in training_ids
        }
        means = {
            name: float(np.mean([row[name] for row in coordinate_rows.values()]))
            for name in coordinate_names
        }
        scales = {
            name: float(np.std([row[name] for row in coordinate_rows.values()])) or 1.0
            for name in coordinate_names
        }
        heldout_coordinates = candidate_coordinates(candidates[heldout])
        equal_weight_score = sum(
            (heldout_coordinates[name] - means[name]) / scales[name] for name in coordinate_names
        )
        heldout_source, heldout_rule = heldout.split("__", 1)
        for epoch in passes:
            training_rows = [
                row for row in rows if row["candidate_id"] != heldout and row["pass"] == epoch
            ]
            global_mean = float(np.mean([row["utility_thz"] for row in training_rows]))

            observed = next(
                row["utility_thz"]
                for row in rows
                if row["candidate_id"] == heldout and row["pass"] == epoch
            )
            scores = {
                "equal_weight_signal_coverage_affinity": equal_weight_score,
                "fixed_source_family_selected_inside_each_training_fold": group_utility_mean(
                    training_rows, 0, heldout_source, global_mean
                ),
                "fixed_selection_rule_selected_inside_each_training_fold": group_utility_mean(
                    training_rows, 1, heldout_rule, global_mean
                ),
                "hash_uniform": float(heldout_rule == "hash_uniform"),
            }
            for name, score in scores.items():
                predictions[name].append(
                    {
                        "candidate_id": heldout,
                        "pass": epoch,
                        "observed": observed,
                        "predicted": score,
                    }
                )

    results = [
        {"name": name, "metrics": decision_metrics(values)} for name, values in predictions.items()
    ]
    random_regrets = []
    for epoch in passes:
        observed = [row["utility_thz"] for row in rows if row["pass"] == epoch]
        random_regrets.append(max(observed) - float(np.mean(observed)))
    results.append(
        {
            "name": "random_choice_expectation",
            "metrics": {
                "pairwise_rank_accuracy": 0.5,
                "best_environment_decisions": None,
                "decision_count": len(passes),
                "mean_allocation_regret_thz": float(np.mean(random_regrets)),
            },
        }
    )
    return results


def group_utility_mean(rows: list[dict], field_index: int, value: str, fallback: float) -> float:
    matches = [
        row["utility_thz"]
        for row in rows
        if row["candidate_id"].split("__", 1)[field_index] == value
    ]
    return float(np.mean(matches)) if matches else fallback


def freeze_prospective_baselines(
    rows: list[dict],
    prospective_ids: list[str],
    passes: list[int],
    baseline_ranking: list[dict],
) -> list[dict]:
    rank_by_id = {row["candidate_id"]: row["rank"] for row in baseline_ranking}
    records = []
    for epoch in passes:
        training_rows = [row for row in rows if row["pass"] == epoch]
        global_mean = float(np.mean([row["utility_thz"] for row in training_rows]))
        source_scores = {
            candidate_id: group_utility_mean(
                training_rows, 0, candidate_id.split("__", 1)[0], global_mean
            )
            for candidate_id in prospective_ids
        }
        rule_scores = {
            candidate_id: group_utility_mean(
                training_rows, 1, candidate_id.split("__", 1)[1], global_mean
            )
            for candidate_id in prospective_ids
        }

        def winners(scores: dict[str, float]) -> list[str]:
            best = max(scores.values())
            return sorted(candidate_id for candidate_id, score in scores.items() if score == best)

        hash_uniform = sorted(
            candidate_id
            for candidate_id in prospective_ids
            if candidate_id.split("__", 1)[1] == "hash_uniform"
        )
        records.extend(
            [
                {
                    "name": "equal_weight_signal_coverage_affinity",
                    "pass": epoch,
                    "selected_candidates": [
                        min(prospective_ids, key=lambda item: (rank_by_id[item], item))
                    ],
                },
                {
                    "name": "fixed_source_family_selected_on_development",
                    "pass": epoch,
                    "selected_candidates": winners(source_scores),
                },
                {
                    "name": "fixed_selection_rule_selected_on_development",
                    "pass": epoch,
                    "selected_candidates": winners(rule_scores),
                },
                {
                    "name": "hash_uniform",
                    "pass": epoch,
                    "selected_candidates": hash_uniform,
                    "applicable": bool(hash_uniform),
                },
                {
                    "name": "random_choice_expectation",
                    "pass": epoch,
                    "selected_candidates": prospective_ids,
                },
            ]
        )
    return records


def cross_validate(
    rows: list[dict], candidates: dict[str, dict], features: list[str], passes: list[int]
) -> tuple[list[dict], dict]:
    predictions = []
    for heldout in sorted({row["candidate_id"] for row in rows}):
        training = [row for row in rows if row["candidate_id"] != heldout]
        model = fit_surface(training, candidates, features, passes)
        for row in rows:
            if row["candidate_id"] == heldout:
                predictions.append(
                    {
                        "candidate_id": heldout,
                        "pass": row["pass"],
                        "observed": row["utility_thz"],
                        "predicted": predict_surface(model, candidates[heldout], row["pass"]),
                    }
                )
    return predictions, decision_metrics(predictions)


def fit(
    panel_path: Path,
    decision_protocol_path: Path,
    modeling_protocol_path: Path,
    outcomes_path: Path,
) -> dict:
    panel = json.loads(panel_path.read_text(encoding="utf-8"))
    decision = json.loads(decision_protocol_path.read_text(encoding="utf-8"))
    modeling = json.loads(modeling_protocol_path.read_text(encoding="utf-8"))
    outcomes = json.loads(outcomes_path.read_text(encoding="utf-8"))
    if any(outcomes["prospective_boundary"].values()):
        raise ValueError("development outcome artifact crosses the prospective boundary")
    candidates = {candidate["candidate_id"]: candidate for candidate in panel["candidates"]}
    rows = outcomes["seed_mean_curves"]
    passes = sorted({row["pass"] for row in rows})
    comparisons = []
    prediction_sets = {}
    definitions = modeling["aggregate_utility"]["candidate_predictors"]
    for name, features in definitions.items():
        predictions, metrics = cross_validate(rows, candidates, features, passes)
        prediction_sets[name] = predictions
        comparisons.append(
            {
                "name": name,
                "features": features,
                "metrics": metrics,
                "parameters": len(passes) + len(features),
            }
        )
    comparisons.sort(
        key=lambda item: (
            item["metrics"]["curve_rmse_thz"],
            -item["metrics"]["pairwise_rank_accuracy"],
            item["metrics"]["mean_allocation_regret_thz"],
            len(item["features"]),
        )
    )
    selected = comparisons[0]
    selected_predictions = prediction_sets[selected["name"]]
    residual_by_environment = {}
    for candidate_id in sorted({row["candidate_id"] for row in selected_predictions}):
        residual_by_environment[candidate_id] = max(
            abs(row["predicted"] - row["observed"])
            for row in selected_predictions
            if row["candidate_id"] == candidate_id
        )
    envelope = float(np.quantile(list(residual_by_environment.values()), 0.9, method="higher"))
    development_ids = {
        candidate_id
        for candidate_id in candidates
        if candidates[candidate_id]["role"] == "development"
    }
    final_model = fit_surface(
        rows,
        {key: value for key, value in candidates.items() if key in development_ids},
        selected["features"],
        passes,
    )
    prospective = []
    for candidate in panel["candidates"]:
        if candidate["role"] != "prospective":
            continue
        prospective.append(
            {
                "candidate_id": candidate["candidate_id"],
                "curve": [
                    {
                        "pass": epoch,
                        "predicted_utility_thz": predict_surface(final_model, candidate, epoch),
                        "empirical_half_width_thz": envelope,
                    }
                    for epoch in passes
                ],
            }
        )
    for epoch in passes:
        ranking = sorted(
            prospective,
            key=lambda item: next(
                point["predicted_utility_thz"] for point in item["curve"] if point["pass"] == epoch
            ),
            reverse=True,
        )
        for rank, item in enumerate(ranking, start=1):
            next(point for point in item["curve"] if point["pass"] == epoch)["rank"] = rank
    baseline_ranking = decision["literature_derived_baseline"]["ranking"]
    prospective_ids = sorted(item["candidate_id"] for item in prospective)
    return {
        "artifact": "anarres_mlip_aggregate_utility_fit_v1",
        "status": "selected_on_development_before_prospective_training",
        "inputs": {
            "candidate_panel_sha256": sha256(panel_path),
            "decision_protocol_sha256": sha256(decision_protocol_path),
            "development_modeling_protocol_sha256": sha256(modeling_protocol_path),
            "development_outcomes_sha256": sha256(outcomes_path),
        },
        "model_comparison": comparisons,
        "allocation_baselines": allocation_baselines(rows, candidates, passes),
        "selected_model": {
            "name": selected["name"],
            "features": selected["features"],
            "cross_validation": selected["metrics"],
            "curve_envelope_half_width_thz": envelope,
            "fit": final_model,
        },
        "prospective_forecast": prospective,
        "baseline_ranking": baseline_ranking,
        "prospective_baseline_decisions": freeze_prospective_baselines(
            rows, prospective_ids, passes, baseline_ranking
        ),
        "prospective_boundary": {
            "prospective_candidate_training_outcomes_used": False,
            "prospective_target_outcomes_used": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--decision-protocol", type=Path, required=True)
    parser.add_argument("--modeling-protocol", type=Path, required=True)
    parser.add_argument("--development-outcomes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = fit(
        args.panel,
        args.decision_protocol,
        args.modeling_protocol,
        args.development_outcomes,
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
