#!/usr/bin/env python3
"""Select target-regression predictors and freeze prospective probabilities."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.stats import rankdata

PENALTIES = (0.1, 1.0, 10.0)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sigmoid(values: np.ndarray) -> np.ndarray:
    positive = values >= 0
    result = np.empty_like(values, dtype=float)
    result[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    exponential = np.exp(values[~positive])
    result[~positive] = exponential / (1.0 + exponential)
    return result


def numeric_values(row: dict, candidate: dict) -> dict[str, float]:
    descriptor = row["target_descriptor"]
    support = row["chemical_support"]
    affinity = row["nearest_neighbor_affinity"]
    return {
        "log_starting_frequency_mae": math.log(descriptor["starting_frequency_mae_thz"]),
        "starting_predicted_stability_margin_kelvin": descriptor[
            "starting_predicted_stability_margin_kelvin"
        ],
        "target_element_count": descriptor["element_count"],
        "target_unitcell_atoms": descriptor["unitcell_atoms"],
        "log_signal_density": math.log(candidate["signal_density_per_atom"]),
        "effective_signal_coverage": candidate["effective_signal_coverage"],
        "mean_target_affinity": candidate["mean_target_affinity"],
        "element_distribution_overlap": support["element_distribution_overlap"],
        "record_fraction_containing_all_target_elements": support[
            "record_fraction_containing_all_target_elements"
        ],
        "top_five_percent_element_set_jaccard": affinity["top_five_percent_element_set_jaccard"],
    }


def expanded_features(definition: list[str], definitions: dict[str, list[str]]) -> list[str]:
    output = []
    for name in definition:
        if name in definitions:
            output.extend(expanded_features(definitions[name], definitions))
        else:
            output.append(name)
    return output


def design_state(rows: list[dict], candidates: dict[str, dict], definition: list[str]) -> dict:
    numeric_names = [name for name in definition if not name.startswith("one_hot_")]
    values = {
        name: [numeric_values(row, candidates[row["candidate_id"]])[name] for row in rows]
        for name in numeric_names
    }
    means = {name: float(np.mean(column)) for name, column in values.items()}
    scales = {name: float(np.std(column)) or 1.0 for name, column in values.items()}
    categories = {}
    if "one_hot_source_family" in definition:
        categories["source_family"] = sorted({row["source_family"] for row in rows})
    if "one_hot_selection_rule" in definition:
        categories["selection_rule"] = sorted({row["selection_rule"] for row in rows})
    if "one_hot_candidate_id" in definition:
        categories["candidate_id"] = sorted({row["candidate_id"] for row in rows})
    return {
        "definition": definition,
        "numeric_names": numeric_names,
        "means": means,
        "scales": scales,
        "categories": categories,
    }


def design(rows: list[dict], candidates: dict[str, dict], state: dict) -> np.ndarray:
    matrix = []
    for row in rows:
        values = numeric_values(row, candidates[row["candidate_id"]])
        vector = [1.0]
        vector.extend(
            (values[name] - state["means"][name]) / state["scales"][name]
            for name in state["numeric_names"]
        )
        for field, categories in state["categories"].items():
            vector.extend(float(row[field] == category) for category in categories)
        matrix.append(vector)
    return np.asarray(matrix, dtype=float)


def fit_logistic(
    rows: list[dict],
    labels: np.ndarray,
    candidates: dict[str, dict],
    definition: list[str],
    penalty: float,
) -> dict:
    state = design_state(rows, candidates, definition)
    matrix = design(rows, candidates, state)
    if len(np.unique(labels)) == 1:
        probability = float((labels.sum() + 1.0) / (len(labels) + 2.0))
        state.update({"constant_probability": probability, "penalty": penalty})
        return state

    def objective(coefficients: np.ndarray) -> tuple[float, np.ndarray]:
        probabilities = sigmoid(matrix @ coefficients)
        probabilities = np.clip(probabilities, 1e-12, 1.0 - 1e-12)
        loss = -np.mean(
            labels * np.log(probabilities) + (1.0 - labels) * np.log(1.0 - probabilities)
        )
        loss += 0.5 * penalty * float(np.dot(coefficients[1:], coefficients[1:]))
        gradient = matrix.T @ (probabilities - labels) / len(labels)
        gradient[1:] += penalty * coefficients[1:]
        return loss, gradient

    result = minimize(
        objective,
        np.zeros(matrix.shape[1]),
        method="L-BFGS-B",
        jac=True,
    )
    if not result.success or not np.all(np.isfinite(result.x)):
        raise ValueError(f"logistic fit failed: {result.message}")
    state.update({"coefficients": result.x.tolist(), "penalty": penalty})
    return state


def predict_logistic(model: dict, rows: list[dict], candidates: dict[str, dict]) -> np.ndarray:
    if "constant_probability" in model:
        return np.full(len(rows), model["constant_probability"])
    return sigmoid(design(rows, candidates, model) @ np.asarray(model["coefficients"]))


def metrics(labels: np.ndarray, probabilities: np.ndarray) -> dict:
    positives = int(labels.sum())
    negatives = len(labels) - positives
    if positives and negatives:
        ranks = rankdata(probabilities, method="average")
        auc = float(
            (ranks[labels == 1].sum() - positives * (positives + 1) / 2) / (positives * negatives)
        )
    else:
        auc = None
    if positives:
        order = np.argsort(-probabilities, kind="stable")
        ordered = labels[order]
        precision = np.cumsum(ordered) / np.arange(1, len(labels) + 1)
        average_precision = float((precision * ordered).sum() / positives)
        top_count = max(1, math.ceil(0.2 * len(labels)))
        top_recall = float(ordered[:top_count].sum() / positives)
    else:
        average_precision = None
        top_recall = None
    return {
        "roc_auc": auc,
        "average_precision": average_precision,
        "brier_score": float(np.mean((probabilities - labels) ** 2)),
        "recall_in_top_risk_20_percent": top_recall,
        "positive_rate": positives / len(labels),
        "examples": len(labels),
    }


def macro_metrics(labels: np.ndarray, probabilities: np.ndarray, groups: list[str]) -> dict:
    per_group = []
    for group in sorted(set(groups)):
        indices = [index for index, value in enumerate(groups) if value == group]
        per_group.append(metrics(labels[indices], probabilities[indices]))
    names = (
        "roc_auc",
        "average_precision",
        "brier_score",
        "recall_in_top_risk_20_percent",
        "positive_rate",
    )
    return {
        name: float(np.mean([row[name] for row in per_group if row[name] is not None]))
        if any(row[name] is not None for row in per_group)
        else None
        for name in names
    } | {"groups": len(per_group)}


def grouped_predictions(
    rows: list[dict],
    labels: np.ndarray,
    candidates: dict[str, dict],
    definition: list[str],
    groups: list[str],
) -> tuple[np.ndarray, list[float]]:
    probabilities = np.zeros(len(rows))
    chosen_penalties = []
    group_values = sorted(set(groups))
    for heldout in group_values:
        train_indices = [index for index, group in enumerate(groups) if group != heldout]
        test_indices = [index for index, group in enumerate(groups) if group == heldout]
        train_rows = [rows[index] for index in train_indices]
        train_labels = labels[train_indices]
        train_groups = [groups[index] for index in train_indices]
        penalty_scores = []
        for penalty in PENALTIES:
            inner_predictions = np.zeros(len(train_rows))
            inner_valid = True
            for inner_heldout in sorted(set(train_groups)):
                inner_train = [
                    index for index, group in enumerate(train_groups) if group != inner_heldout
                ]
                inner_test = [
                    index for index, group in enumerate(train_groups) if group == inner_heldout
                ]
                if not inner_train:
                    inner_valid = False
                    break
                model = fit_logistic(
                    [train_rows[index] for index in inner_train],
                    train_labels[inner_train],
                    candidates,
                    definition,
                    penalty,
                )
                inner_predictions[inner_test] = predict_logistic(
                    model,
                    [train_rows[index] for index in inner_test],
                    candidates,
                )
            score = (
                float(np.mean((inner_predictions - train_labels) ** 2))
                if inner_valid
                else float("inf")
            )
            penalty_scores.append((score, penalty))
        chosen = min(penalty_scores)[1]
        chosen_penalties.append(chosen)
        model = fit_logistic(train_rows, train_labels, candidates, definition, chosen)
        probabilities[test_indices] = predict_logistic(
            model, [rows[index] for index in test_indices], candidates
        )
    return probabilities, chosen_penalties


def evaluate_negative_controls(
    rows: list[dict],
    labels: np.ndarray,
    candidates: dict[str, dict],
    selected_features: list[str],
    environment_groups: list[str],
    target_groups: list[str],
    comparisons: list[dict],
) -> dict:
    starting = next(item for item in comparisons if item["name"] == "starting_error_only")
    identity_probabilities, identity_penalties = grouped_predictions(
        rows,
        labels,
        candidates,
        ["one_hot_candidate_id"],
        target_groups,
    )
    permutation_seed = 0
    permuted_labels = np.random.default_rng(permutation_seed).permutation(labels)
    permuted_probabilities, permuted_penalties = grouped_predictions(
        rows,
        permuted_labels,
        candidates,
        selected_features,
        environment_groups,
    )
    return {
        "starting_checkpoint_error_only": {
            "evaluation": "leave_one_environment_out",
            "metrics": starting["metrics"],
        },
        "candidate_identity_only": {
            "evaluation": "leave_one_target_material_out",
            "metrics": metrics(labels, identity_probabilities),
            "outer_fold_penalties": identity_penalties,
        },
        "permuted_regression_labels": {
            "evaluation": "leave_one_environment_out",
            "permutation_seed": permutation_seed,
            "metrics_against_permuted_labels": metrics(permuted_labels, permuted_probabilities),
            "outer_fold_penalties": permuted_penalties,
        },
    }


def fit(
    panel_path: Path,
    modeling_protocol_path: Path,
    outcomes_path: Path,
    feature_path: Path,
) -> dict:
    panel = json.loads(panel_path.read_text(encoding="utf-8"))
    protocol = json.loads(modeling_protocol_path.read_text(encoding="utf-8"))
    outcomes = json.loads(outcomes_path.read_text(encoding="utf-8"))
    feature_artifact = json.loads(feature_path.read_text(encoding="utf-8"))
    if any(outcomes["prospective_boundary"].values()):
        raise ValueError("development outcomes cross the prospective boundary")
    candidates = {candidate["candidate_id"]: candidate for candidate in panel["candidates"]}
    feature_rows = {
        (row["candidate_id"], row["target_material_id"]): row
        for row in feature_artifact["features"]
    }
    rows = []
    labels = []
    for outcome in outcomes["target_regressions"]:
        row = dict(feature_rows[(outcome["candidate_id"], outcome["target_material_id"])])
        rows.append(row)
        labels.append(float(outcome["frequency_error_regression"]))
    labels_array = np.asarray(labels)
    definitions = protocol["target_regressions"]["candidate_models"]
    comparisons = []
    prediction_sets = {}
    environment_groups = [row["candidate_id"] for row in rows]
    for name, raw_definition in definitions.items():
        definition = expanded_features(raw_definition, definitions)
        probabilities, penalties = grouped_predictions(
            rows, labels_array, candidates, definition, environment_groups
        )
        result_metrics = metrics(labels_array, probabilities)
        comparisons.append(
            {
                "name": name,
                "features": definition,
                "metrics": result_metrics,
                "outer_fold_penalties": penalties,
            }
        )
        prediction_sets[name] = probabilities
    comparisons.sort(
        key=lambda item: (
            item["metrics"]["brier_score"],
            -(item["metrics"]["average_precision"] or -1.0),
            -(item["metrics"]["roc_auc"] or -1.0),
            len(item["features"]),
        )
    )
    selected = comparisons[0]
    penalty_scores = []
    for penalty in PENALTIES:
        probabilities = np.zeros(len(rows))
        for heldout in sorted(set(environment_groups)):
            train = [index for index, group in enumerate(environment_groups) if group != heldout]
            test = [index for index, group in enumerate(environment_groups) if group == heldout]
            model = fit_logistic(
                [rows[index] for index in train],
                labels_array[train],
                candidates,
                selected["features"],
                penalty,
            )
            probabilities[test] = predict_logistic(
                model, [rows[index] for index in test], candidates
            )
        penalty_scores.append((metrics(labels_array, probabilities)["brier_score"], penalty))
    selected_penalty = min(penalty_scores)[1]
    final_model = fit_logistic(
        rows, labels_array, candidates, selected["features"], selected_penalty
    )
    selected_probabilities = prediction_sets[selected["name"]]
    target_groups = [row["target_material_id"] for row in rows]
    chemistry_groups = ["-".join(row["target_descriptor"]["elements"]) for row in rows]
    source_groups = [row["source_family"] for row in rows]
    secondary = {}
    for name, groups in (
        ("leave_one_target_material_out", target_groups),
        ("leave_one_target_element_set_out", chemistry_groups),
    ):
        probabilities, penalties = grouped_predictions(
            rows, labels_array, candidates, selected["features"], groups
        )
        secondary[name] = {
            "metrics": metrics(labels_array, probabilities),
            "outer_fold_penalties": penalties,
        }
    negative_controls = evaluate_negative_controls(
        rows,
        labels_array,
        candidates,
        selected["features"],
        environment_groups,
        target_groups,
        comparisons,
    )
    prospective_rows = [
        row
        for row in feature_artifact["features"]
        if row["candidate_role"] == "prospective" and row["target_role"] == "prospective"
    ]
    prospective_probabilities = predict_logistic(final_model, prospective_rows, candidates)
    prospective = [
        {
            "candidate_id": row["candidate_id"],
            "target_material_id": row["target_material_id"],
            "frequency_error_regression_probability": float(probability),
        }
        for row, probability in zip(prospective_rows, prospective_probabilities, strict=True)
    ]
    return {
        "artifact": "anarres_mlip_target_regression_fit_v1",
        "status": "selected_on_development_before_prospective_training",
        "inputs": {
            "candidate_panel_sha256": sha256(panel_path),
            "development_modeling_protocol_sha256": sha256(modeling_protocol_path),
            "development_outcomes_sha256": sha256(outcomes_path),
            "target_regression_features_sha256": sha256(feature_path),
        },
        "model_comparison": comparisons,
        "negative_controls": negative_controls,
        "selected_model": {
            "name": selected["name"],
            "features": selected["features"],
            "primary_cross_validation": selected["metrics"],
            "primary_macro_metrics": {
                "environment": macro_metrics(
                    labels_array, selected_probabilities, environment_groups
                ),
                "source_family": macro_metrics(labels_array, selected_probabilities, source_groups),
            },
            "secondary_cross_validation": secondary,
            "penalty": selected_penalty,
            "fit": final_model,
        },
        "development_predictions": [
            {
                "candidate_id": row["candidate_id"],
                "target_material_id": row["target_material_id"],
                "observed": bool(label),
                "predicted_probability": float(probability),
            }
            for row, label, probability in zip(
                rows, labels_array, selected_probabilities, strict=True
            )
        ],
        "prospective_predictions": prospective,
        "prospective_boundary": {
            "prospective_candidate_training_outcomes_used": False,
            "prospective_target_outcomes_used": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--modeling-protocol", type=Path, required=True)
    parser.add_argument("--development-outcomes", type=Path, required=True)
    parser.add_argument("--target-features", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = fit(
        args.panel,
        args.modeling_protocol,
        args.development_outcomes,
        args.target_features,
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
