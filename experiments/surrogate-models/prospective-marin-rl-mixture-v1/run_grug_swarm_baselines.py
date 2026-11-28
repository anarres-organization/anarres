#!/usr/bin/env python3
"""Run transparent lineage-safe baselines on the released Grug mixture swarm."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections.abc import Callable
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
INPUTS = HERE / "GRUG_SWARM_INPUTS.jsonl.gz"
LABELS = HERE / "GRUG_SWARM_PROTECTED_LABELS.jsonl.gz"
CORPUS = HERE / "GRUG_SWARM_CORPUS.json"
CONTENT = HERE / "GRUG_SWARM_CONTENT_BASIS.json.gz"
RESULTS = HERE / "GRUG_SWARM_BASELINE_RESULTS.json"

RIDGE_ALPHA = 100.0
KERNEL_ALPHA = 1.0
KERNEL_GAMMA_MULTIPLIER = 0.25


def read_rows(path: Path) -> list[dict]:
    with gzip.open(path, "rt") as stream:
        return [json.loads(line) for line in stream]


def read_gzip_json(path: Path) -> dict:
    with gzip.open(path, "rt") as stream:
        return json.load(stream)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lineage_fold(lineage: str) -> str:
    value = int(hashlib.sha256(lineage.encode()).hexdigest()[:8], 16) % 5
    return f"lineage_fold_{value}"


def squared_distance(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    result = (
        np.sum(left * left, axis=1)[:, None]
        + np.sum(right * right, axis=1)[None, :]
        - 2 * left @ right.T
    )
    return np.maximum(result, 0.0)


def mean_predictor(_: np.ndarray, train_y: np.ndarray, test_x: np.ndarray) -> np.ndarray:
    return np.repeat(train_y.mean(axis=0)[None, :], len(test_x), axis=0)


def ridge_predictor(train_x: np.ndarray, train_y: np.ndarray, test_x: np.ndarray) -> np.ndarray:
    x_mean = train_x.mean(axis=0)
    x_scale = train_x.std(axis=0)
    x_scale[x_scale < 1e-12] = 1.0
    y_mean = train_y.mean(axis=0)
    y_scale = train_y.std(axis=0)
    y_scale[y_scale < 1e-12] = 1.0
    x = (train_x - x_mean) / x_scale
    y = (train_y - y_mean) / y_scale
    test = (test_x - x_mean) / x_scale
    left, singular, right = np.linalg.svd(x, full_matrices=False)
    weights = right.T * (singular / (singular * singular + RIDGE_ALPHA))
    prediction = test @ (weights @ (left.T @ y))
    return y_mean + y_scale * prediction


def kernel_predictor(train_x: np.ndarray, train_y: np.ndarray, test_x: np.ndarray) -> np.ndarray:
    train = np.sqrt(np.maximum(train_x, 0.0))
    test = np.sqrt(np.maximum(test_x, 0.0))
    y_mean = train_y.mean(axis=0)
    y_scale = train_y.std(axis=0)
    y_scale[y_scale < 1e-12] = 1.0
    y = (train_y - y_mean) / y_scale
    distance = squared_distance(train, train)
    positive = distance[distance > 0]
    gamma = KERNEL_GAMMA_MULTIPLIER / np.median(positive)
    kernel = np.exp(-gamma * distance)
    kernel.flat[:: len(kernel) + 1] += KERNEL_ALPHA
    coefficients = np.linalg.solve(kernel, y)
    prediction = np.exp(-gamma * squared_distance(test, train)) @ coefficients
    return y_mean + y_scale * prediction


def aggregate_lineages(
    observed: np.ndarray,
    predicted: np.ndarray,
    folds: np.ndarray,
    lineages: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    observed_rows = []
    predicted_rows = []
    fold_rows = []
    for fold in sorted(set(folds)):
        for lineage in sorted(set(lineages[folds == fold])):
            selected = (folds == fold) & (lineages == lineage)
            observed_rows.append(observed[selected].mean(axis=0))
            predicted_rows.append(predicted[selected].mean(axis=0))
            fold_rows.append(fold)
    return (
        np.asarray(observed_rows),
        np.asarray(predicted_rows),
        np.asarray(fold_rows),
    )


def decision_metrics(
    observed: np.ndarray, predicted: np.ndarray, folds: np.ndarray
) -> dict[str, float]:
    fold_accuracies = []
    fold_regrets = []
    correct = 0.0
    pairs = 0
    for fold in sorted(set(folds)):
        indices = np.where(folds == fold)[0]
        fold_correct = 0.0
        fold_pairs = 0
        for offset, left in enumerate(indices):
            right = indices[offset + 1 :]
            if not len(right):
                continue
            observed_change = observed[right] - observed[left]
            predicted_change = predicted[right] - predicted[left]
            score = np.where(
                predicted_change == 0,
                0.5,
                (np.sign(observed_change) == np.sign(predicted_change)).astype(float),
            )
            fold_correct += float(score.sum())
            fold_pairs += int(score.size)
        if fold_pairs:
            fold_accuracies.append(fold_correct / fold_pairs)
            correct += fold_correct
            pairs += fold_pairs

        observed_fold = observed[indices]
        predicted_fold = predicted[indices]
        best = np.min(observed_fold, axis=0)
        worst = np.max(observed_fold, axis=0)
        chosen = np.argmin(predicted_fold, axis=0)
        chosen_observed = observed_fold[chosen, np.arange(observed.shape[1])]
        span = worst - best
        regret = np.divide(
            chosen_observed - best,
            span,
            out=np.zeros_like(span),
            where=span > 0,
        )
        fold_regrets.append(float(np.mean(regret)))
    return {
        "pair_weighted_pairwise_ordering_accuracy": correct / pairs,
        "fold_macro_pairwise_ordering_accuracy": float(np.mean(fold_accuracies)),
        "fold_macro_normalized_allocation_regret": float(np.mean(fold_regrets)),
    }


def evaluate(
    x: np.ndarray,
    y: np.ndarray,
    folds: np.ndarray,
    lineages: np.ndarray,
    predictor: Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray],
) -> tuple[np.ndarray, dict]:
    predictions = np.zeros_like(y)
    standardized_errors = np.zeros_like(y)
    for fold in sorted(set(folds)):
        test = folds == fold
        train = ~test
        scale = y[train].std(axis=0)
        scale[scale < 1e-12] = 1.0
        predictions[test] = predictor(x[train], y[train], x[test])
        standardized_errors[test] = (predictions[test] - y[test]) / scale
    target_nrmse = np.sqrt(np.mean(standardized_errors**2, axis=0))
    correlations = []
    for target in range(y.shape[1]):
        if np.std(predictions[:, target]) < 1e-12:
            correlations.append(0.0)
        else:
            correlations.append(float(np.corrcoef(y[:, target], predictions[:, target])[0, 1]))
    lineage_observed, lineage_predicted, lineage_folds = aggregate_lineages(
        y, predictions, folds, lineages
    )
    metrics = {
        "mean_target_normalized_rmse": float(np.mean(target_nrmse)),
        "median_target_normalized_rmse": float(np.median(target_nrmse)),
        "mean_target_pearson": float(np.mean(correlations)),
    }
    metrics.update(decision_metrics(lineage_observed, lineage_predicted, lineage_folds))
    return predictions, metrics


def support_gate_audit(
    x: np.ndarray,
    y: np.ndarray,
    folds: np.ndarray,
    lineages: np.ndarray,
) -> dict:
    accepted_errors = []
    rejected_errors = []
    accepted_lineages = 0
    total_lineages = 0
    folds_with_abstention = 0
    transformed = np.sqrt(np.maximum(x, 0.0))
    for fold in sorted(set(folds)):
        test = folds == fold
        train = ~test
        prediction = kernel_predictor(x[train], y[train], x[test])
        train_distance = squared_distance(transformed[train], transformed[train])
        train_lineages = lineages[train]
        train_distance[train_lineages[:, None] == train_lineages[None, :]] = np.inf
        nearest_train = np.sqrt(np.min(train_distance, axis=1))
        threshold = float(np.quantile(nearest_train, 0.95))
        test_distance = np.sqrt(
            np.min(squared_distance(transformed[test], transformed[train]), axis=1)
        )
        scale = y[train].std(axis=0)
        scale[scale < 1e-12] = 1.0
        row_error = np.mean(np.abs((prediction - y[test]) / scale), axis=1)
        test_lineages = lineages[test]
        fold_abstained = False
        for lineage in sorted(set(test_lineages)):
            selected = test_lineages == lineage
            distance = float(np.mean(test_distance[selected]))
            error = float(np.mean(row_error[selected]))
            total_lineages += 1
            if distance <= threshold:
                accepted_lineages += 1
                accepted_errors.append(error)
            else:
                rejected_errors.append(error)
                fold_abstained = True
        folds_with_abstention += int(fold_abstained)
    return {
        "calibration_rule": (
            "accept when the test mixture's Hellinger distance to training support "
            "does not exceed the training fold's 95th-percentile leave-one-lineage-out distance"
        ),
        "accepted_lineage_fraction": accepted_lineages / total_lineages,
        "accepted_mean_absolute_standardized_error": float(np.mean(accepted_errors)),
        "rejected_mean_absolute_standardized_error": float(np.mean(rejected_errors)),
        "rejected_lineages": len(rejected_errors),
        "folds_with_any_abstention": folds_with_abstention,
        "folds": len(set(folds)),
    }


def rounded(value):
    if isinstance(value, float):
        return round(value, 8)
    if isinstance(value, dict):
        return {key: rounded(item) for key, item in value.items()}
    if isinstance(value, list):
        return [rounded(item) for item in value]
    return value


def build_results() -> dict:
    inputs = read_rows(INPUTS)
    labels_by_key = {row["record_key"]: row for row in read_rows(LABELS)}
    target_rows = labels_by_key[inputs[0]["record_key"]]["outcomes"]
    target_names = [row["metric"] for row in target_rows]
    target_families = [row["family"] for row in target_rows]
    x = np.asarray(
        [
            row["prediction_time"]["phase0_cell_weights"]
            + row["prediction_time"]["phase1_cell_weights"]
            for row in inputs
        ],
        dtype=float,
    )
    content_basis = np.asarray(read_gzip_json(CONTENT)["matrix"], dtype=float)
    content_x = np.concatenate([x[:, :200] @ content_basis, x[:, 200:] @ content_basis], axis=1)
    y = np.asarray(
        [
            [outcome["value"] for outcome in labels_by_key[row["record_key"]]["outcomes"]]
            for row in inputs
        ],
        dtype=float,
    )
    lineages = np.asarray([row["lineage_key"] for row in inputs])
    split_schemes = {
        "lineage_five_fold": np.asarray([lineage_fold(lineage) for lineage in lineages]),
        "leave_one_design_family_out": np.asarray([row["design_family"] for row in inputs]),
    }
    models = {
        "training_mean": (x, mean_predictor),
        "linear_ridge": (x, ridge_predictor),
        "hellinger_rbf_kernel": (x, kernel_predictor),
        "content_hellinger_rbf_kernel": (content_x, kernel_predictor),
    }
    results = {}
    predictions_by_scheme = {}
    for scheme, folds in split_schemes.items():
        results[scheme] = {}
        predictions_by_scheme[scheme] = {}
        for name, (features, predictor) in models.items():
            predictions, metrics = evaluate(features, y, folds, lineages, predictor)
            predictions_by_scheme[scheme][name] = predictions
            by_family = {}
            for family in sorted(set(target_families)):
                indices = np.asarray(
                    [index for index, value in enumerate(target_families) if value == family]
                )
                _, family_metrics = evaluate(features, y[:, indices], folds, lineages, predictor)
                by_family[family] = family_metrics
            results[scheme][name] = {"all_targets": metrics, "by_target_family": by_family}

    support_gate = {
        "model": "content_hellinger_rbf_kernel",
        "results": {
            scheme: support_gate_audit(content_x, y, folds, lineages)
            for scheme, folds in split_schemes.items()
        },
    }

    baseline_lineage = "mixture-b5f5f18766de58f382ac9774"
    selected_lineage = "mixture-ceefb8ecb2e51e5bb618a553"
    held_out = (lineages == baseline_lineage) | (lineages == selected_lineage)
    trained = ~held_out
    selected_comparison = {}
    for name, (features, predictor) in models.items():
        predictions = predictor(features[trained], y[trained], features[held_out])
        comparison = {}
        for family in sorted(set(target_families)):
            target_indices = np.asarray(
                [index for index, value in enumerate(target_families) if value == family]
            )
            observed_baseline = y[lineages == baseline_lineage][:, target_indices].mean(axis=0)
            observed_selected = y[lineages == selected_lineage][:, target_indices].mean(axis=0)
            predicted_baseline = predictions[lineages[held_out] == baseline_lineage][
                :, target_indices
            ].mean(axis=0)
            predicted_selected = predictions[lineages[held_out] == selected_lineage][
                :, target_indices
            ].mean(axis=0)
            observed_change = observed_selected - observed_baseline
            predicted_change = predicted_selected - predicted_baseline
            correct = np.where(
                predicted_change == 0,
                0.5,
                (np.sign(observed_change) == np.sign(predicted_change)).astype(float),
            )
            directions = {}
            for local_index, target_index in enumerate(target_indices):

                def direction(value: float) -> str:
                    if value < 0:
                        return "improved"
                    if value > 0:
                        return "regressed"
                    return "tied"

                directions[target_names[target_index]] = {
                    "observed": direction(float(observed_change[local_index])),
                    "predicted": direction(float(predicted_change[local_index])),
                }
            comparison[family] = {
                "targets": len(target_indices),
                "observed_selected_wins": int(np.sum(observed_change < 0)),
                "predicted_selected_wins": int(np.sum(predicted_change < 0)),
                "ordering_accuracy": float(np.mean(correct)),
                "directions": directions,
            }
        selected_comparison[name] = comparison

    return rounded(
        {
            "artifact": "anarres_grug_swarm_transparent_baselines_v1",
            "status": "retrospective development result; not a prospective claim",
            "inputs": {
                "corpus_manifest_sha256": digest(CORPUS),
                "inputs_sha256": digest(INPUTS),
                "protected_labels_sha256": digest(LABELS),
                "content_basis_sha256": digest(CONTENT),
                "trained_runs": len(inputs),
                "candidate_lineages": len(set(lineages)),
                "targets": len(target_names),
            },
            "models": {
                "training_mean": "per-target mean of the outer training fold",
                "linear_ridge": {
                    "features": "all 400 two-phase cell weights",
                    "alpha": RIDGE_ALPHA,
                },
                "hellinger_rbf_kernel": {
                    "features": "square roots of all 400 two-phase cell weights",
                    "alpha": KERNEL_ALPHA,
                    "gamma": "0.25 divided by the median positive training distance",
                },
                "content_hellinger_rbf_kernel": {
                    "features": (
                        "two 1,000-bin lexical distributions obtained by multiplying each "
                        "phase's 200 cell weights by Marin's released cell-content basis"
                    ),
                    "alpha": KERNEL_ALPHA,
                    "gamma": "0.25 divided by the median positive training distance",
                },
            },
            "split_contract": {
                "lineage_five_fold": "interpolation check; identical mixtures stay together",
                "leave_one_design_family_out": (
                    "extrapolation check; one construction family is absent from training"
                ),
                "selected_pair": (
                    "the published selected and baseline mixture lineages are both "
                    "absent from training"
                ),
            },
            "results": results,
            "support_gate": support_gate,
            "published_selected_pair": selected_comparison,
            "interpretation_boundary": (
                "The selected mixture was chosen using this swarm. Its held-out replay is a "
                "development diagnostic, not independent evidence. The scale ladder and future "
                "post-training panel remain separate tests."
            ),
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build_results()
    if args.check:
        observed = json.loads(RESULTS.read_text())
        if observed != expected:
            raise SystemExit("stale Grug swarm baseline results")
        return
    RESULTS.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
