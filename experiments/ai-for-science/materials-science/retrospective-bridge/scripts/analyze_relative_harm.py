#!/usr/bin/env python3
"""Estimate relative environment-harm risk under leave-one-source-out tests.

The endpoint is candidate underperformance relative to a prespecified matched
reference environment. It is not absolute degradation from a starting model.
That stronger endpoint is reserved for the sealed prospective phonon study.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BRIDGE_SCRIPT = Path(__file__).with_name("analyze_pooled_semantic.py")
PRIMARY_MARGIN = 0.10
MARGINS = (0.0, PRIMARY_MARGIN, 0.20)
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)
REFERENCE_SOURCES = {
    "li_2023_redundancy",
    "kulichenko_2023_udd",
    "dale_2026_active_learning_failure",
    "bi_elena_2026_budget_crossover",
    "wong_yang_2026_umlip_bias",
    "baghishov_2026_application_specific_mlip",
    "qi_2024_direct_sampling",
    "zhang_2023_etal",
    "espinosa_castaneda_2026_diversity",
    "wang_2026_dataset_aware_entropy",
    "varga_umbrich_2026_force_aware_ntk",
    "kim_2026_density_diversity",
    "haenseroth_dressler_2026_data_efficiency",
}


def load_bridge_module():
    spec = importlib.util.spec_from_file_location("materials_semantic_bridge", BRIDGE_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BRIDGE = load_bridge_module()


def arm_name(source: str, arm: dict) -> str:
    fields = {
        "li_2023_redundancy": "method",
        "kulichenko_2023_udd": "training_environment",
        "dale_2026_active_learning_failure": "acquisition_method",
        "bi_elena_2026_budget_crossover": "selector",
        "wong_yang_2026_umlip_bias": "environment",
        "baghishov_2026_application_specific_mlip": "sampling_method",
        "qi_2024_direct_sampling": "environment",
        "zhang_2023_etal": "environment",
        "espinosa_castaneda_2026_diversity": "environment",
        "wang_2026_dataset_aware_entropy": "environment",
        "varga_umbrich_2026_force_aware_ntk": "environment",
        "kim_2026_density_diversity": "environment",
        "haenseroth_dressler_2026_data_efficiency": "environment",
    }
    return str(arm[fields[source]])


def is_reference(source: str, arm: dict) -> bool:
    name = arm_name(source, arm)
    fixed = {
        "li_2023_redundancy": "random",
        "dale_2026_active_learning_failure": "random",
        "bi_elena_2026_budget_crossover": "Random",
        "wong_yang_2026_umlip_bias": "naive",
        "baghishov_2026_application_specific_mlip": "Random",
        "qi_2024_direct_sampling": "MS",
        "zhang_2023_etal": "rand",
        "espinosa_castaneda_2026_diversity": "random",
        "wang_2026_dataset_aware_entropy": "random_md",
        "varga_umbrich_2026_force_aware_ntk": "random",
        "kim_2026_density_diversity": "no_variance",
        "haenseroth_dressler_2026_data_efficiency": "trajectory_stride_10",
    }
    if source == "kulichenko_2023_udd":
        return name == arm["target_environment"]
    return name == fixed[source]


def standardize_source(source: str, arms: list[dict]) -> list[list[float]]:
    native = [BRIDGE.semantic_coordinates(source, arm) for arm in arms]
    vectors = [[] for _ in arms]
    for coordinate in BRIDGE.COORDINATES:
        observed = [row[coordinate] for row in native if row[coordinate] is not None]
        center = float(np.mean(observed)) if observed else 0.0
        scale = float(np.std(observed)) if observed else 1.0
        if np.isclose(scale, 0.0):
            scale = 1.0
        for vector, row in zip(vectors, native, strict=True):
            value = row[coordinate]
            vector.extend(
                (
                    0.0 if value is None else (float(value) - center) / scale,
                    float(value is None),
                )
            )
    return vectors


def load_pairs(data_dir: Path) -> list[dict]:
    rows = []
    for source, filename in BRIDGE.FILES.items():
        if source not in REFERENCE_SOURCES:
            continue
        payload = json.loads((data_dir / filename).read_text(encoding="utf-8"))
        arms = payload["arms"]
        vectors = standardize_source(source, arms)
        by_panel: dict[str, list[tuple[dict, list[float]]]] = defaultdict(list)
        for arm, vector in zip(arms, vectors, strict=True):
            by_panel[arm["panel_id"]].append((arm, vector))
        for panel, panel_rows in by_panel.items():
            references = [row for row in panel_rows if is_reference(source, row[0])]
            if len(references) != 1:
                raise ValueError(f"{source}:{panel} has {len(references)} reference arms")
            reference, reference_vector = references[0]
            reference_utility = BRIDGE.utility(reference)
            for candidate, candidate_vector in panel_rows:
                if candidate is reference:
                    continue
                delta = np.asarray(candidate_vector) - np.asarray(reference_vector)
                candidate_utility = BRIDGE.utility(candidate)
                rows.append(
                    {
                        "source": source,
                        "panel": panel,
                        "candidate": arm_name(source, candidate),
                        "reference": arm_name(source, reference),
                        "features": delta.tolist(),
                        "semantic_risk_score": -float(np.mean(delta[0::2])),
                        "reference_drop": reference_utility - candidate_utility,
                    }
                )
    return rows


def sigmoid(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-values))


def logistic_predict(
    train: list[dict], test: list[dict], alpha: float, margin: float
) -> np.ndarray:
    x_train = np.asarray([row["features"] for row in train], dtype=float)
    x_test = np.asarray([row["features"] for row in test], dtype=float)
    y = np.asarray([row["reference_drop"] > margin for row in train], dtype=float)
    center = x_train.mean(axis=0)
    scale = x_train.std(axis=0)
    scale[np.isclose(scale, 0.0)] = 1.0
    x_train = (x_train - center) / scale
    x_test = (x_test - center) / scale
    x_train = np.column_stack((np.ones(len(x_train)), x_train))
    x_test = np.column_stack((np.ones(len(x_test)), x_test))
    beta = np.zeros(x_train.shape[1])
    penalty = np.eye(x_train.shape[1]) * alpha
    penalty[0, 0] = 0.0
    for _ in range(100):
        probabilities = sigmoid(x_train @ beta)
        weights = np.clip(probabilities * (1.0 - probabilities), 1e-6, None)
        gradient = x_train.T @ (probabilities - y) + penalty @ beta
        hessian = x_train.T @ (weights[:, None] * x_train) + penalty
        step = np.linalg.solve(hessian, gradient)
        beta -= step
        if np.max(np.abs(step)) < 1e-8:
            break
    return sigmoid(x_test @ beta)


def choose_alpha(train: list[dict], margin: float) -> float:
    sources = sorted({row["source"] for row in train})
    losses = {}
    for alpha in ALPHAS:
        source_losses = []
        for source in sources:
            inner_train = [row for row in train if row["source"] != source]
            inner_test = [row for row in train if row["source"] == source]
            labels = np.asarray([row["reference_drop"] > margin for row in inner_test], dtype=float)
            probabilities = logistic_predict(inner_train, inner_test, alpha, margin)
            source_losses.append(float(np.mean((probabilities - labels) ** 2)))
        losses[alpha] = float(np.mean(source_losses))
    return min(ALPHAS, key=lambda value: (losses[value], value))


def roc_auc(labels: np.ndarray, scores: np.ndarray) -> float | None:
    positives = int(labels.sum())
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return None
    order = np.argsort(scores, kind="stable")
    ranks = np.empty(len(scores), dtype=float)
    start = 0
    while start < len(order):
        stop = start + 1
        while stop < len(order) and scores[order[stop]] == scores[order[start]]:
            stop += 1
        ranks[order[start:stop]] = (start + 1 + stop) / 2.0
        start = stop
    rank_sum = float(ranks[labels == 1].sum())
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def average_precision(labels: np.ndarray, scores: np.ndarray) -> float | None:
    positives = int(labels.sum())
    if positives == 0:
        return None
    order = np.argsort(-scores, kind="stable")
    ranked = labels[order]
    cumulative = np.cumsum(ranked)
    return float(np.sum((cumulative / np.arange(1, len(labels) + 1)) * ranked) / positives)


def single_metrics(rows: list[dict], scores: np.ndarray, margin: float) -> dict:
    labels = np.asarray([row["reference_drop"] > margin for row in rows], dtype=int)
    count = max(1, math.ceil(0.20 * len(rows)))
    top = np.argsort(-scores, kind="stable")[:count]
    positives = int(labels.sum())
    return {
        "pairs": len(rows),
        "adverse_pairs": positives,
        "prevalence": float(labels.mean()),
        "roc_auc": roc_auc(labels, scores),
        "average_precision": average_precision(labels, scores),
        "brier_score": float(np.mean((scores - labels) ** 2)),
        "recall_in_top_risk_20pct": None
        if positives == 0
        else float(labels[top].sum() / positives),
    }


def metrics(rows: list[dict], scores: np.ndarray, margin: float) -> dict:
    pooled = single_metrics(rows, scores, margin)
    per_source = {}
    for source in sorted({row["source"] for row in rows}):
        indices = [index for index, row in enumerate(rows) if row["source"] == source]
        source_rows = [rows[index] for index in indices]
        per_source[source] = single_metrics(source_rows, scores[indices], margin)
    macro = {}
    for key in (
        "prevalence",
        "roc_auc",
        "average_precision",
        "brier_score",
        "recall_in_top_risk_20pct",
    ):
        values = [result[key] for result in per_source.values() if result[key] is not None]
        macro[key] = float(np.mean(values))
        macro[f"{key}_sources"] = len(values)
    return {"pooled": pooled, "source_macro": macro, "per_source": per_source}


def evaluate(rows: list[dict], margin: float, *, tune: bool) -> dict:
    predictions = np.zeros(len(rows), dtype=float)
    semantic_predictions = np.zeros(len(rows), dtype=float)
    alphas = {}
    semantic_alphas = {}
    for source in sorted({row["source"] for row in rows}):
        train = [row for row in rows if row["source"] != source]
        test_indices = [index for index, row in enumerate(rows) if row["source"] == source]
        test = [rows[index] for index in test_indices]
        alpha = choose_alpha(train, margin) if tune else 100.0
        alphas[source] = alpha
        predictions[test_indices] = logistic_predict(train, test, alpha, margin)

        semantic_train = [row | {"features": [row["semantic_risk_score"]]} for row in train]
        semantic_test = [row | {"features": [row["semantic_risk_score"]]} for row in test]
        semantic_alpha = choose_alpha(semantic_train, margin) if tune else 0.01
        semantic_alphas[source] = semantic_alpha
        semantic_predictions[test_indices] = logistic_predict(
            semantic_train, semantic_test, semantic_alpha, margin
        )

    labels = np.asarray([row["reference_drop"] > margin for row in rows], dtype=float)
    prevalence_probabilities = np.zeros(len(rows), dtype=float)
    random_fingerprint = np.zeros(len(rows), dtype=float)
    shuffled_semantic = np.zeros(len(rows), dtype=float)
    for source in sorted({row["source"] for row in rows}):
        train_indices = [index for index, row in enumerate(rows) if row["source"] != source]
        test_indices = [index for index, row in enumerate(rows) if row["source"] == source]
        prevalence_probabilities[test_indices] = float(labels[train_indices].mean())
        for index in test_indices:
            row = rows[index]
            identity = f"{row['source']}|{row['panel']}|{row['candidate']}"
            digest = hashlib.sha256(identity.encode()).digest()
            random_fingerprint[index] = int.from_bytes(digest[:8], "big") / 2**64
        order = sorted(
            test_indices,
            key=lambda index: hashlib.sha256(
                f"shuffle|{rows[index]['panel']}|{rows[index]['candidate']}".encode()
            ).hexdigest(),
        )
        for destination, origin in zip(test_indices, order, strict=True):
            shuffled_semantic[destination] = semantic_predictions[origin]

    return {
        "margin": margin,
        "fold_alphas": alphas,
        "semantic_calibration_fold_alphas": semantic_alphas,
        "prevalence_baseline": metrics(rows, prevalence_probabilities, margin),
        "random_fingerprint_control": metrics(rows, random_fingerprint, margin),
        "shuffled_pairing_control": metrics(rows, shuffled_semantic, margin),
        "semantic_relative_score": metrics(rows, semantic_predictions, margin),
        "fitted_logistic_ridge": metrics(rows, predictions, margin),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path, default=ROOT / "relative_harm_analysis.json")
    args = parser.parse_args()
    rows = load_pairs(args.data)
    primary = evaluate(rows, PRIMARY_MARGIN, tune=True)
    sensitivities = []
    for margin in MARGINS:
        sensitivities.append(
            primary if margin == PRIMARY_MARGIN else evaluate(rows, margin, tune=False)
        )
    result = {
        "artifact": "materials_relative_harm_loso_v1",
        "endpoint": (
            "candidate panel-normalized utility below a prespecified matched reference by more "
            "than the stated margin"
        ),
        "interpretation_boundary": [
            "This endpoint measures relative underperformance against a matched reference arm.",
            "It does not establish absolute degradation from a starting model.",
            "Sources without one outcome-independent reference environment are excluded.",
            "All predictive tests hold out the complete source.",
        ],
        "support": {
            "sources": len({row["source"] for row in rows}),
            "panels": len({(row["source"], row["panel"]) for row in rows}),
            "candidate_reference_pairs": len(rows),
        },
        "primary": primary,
        "margin_sensitivities": sensitivities,
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["support"], indent=2))
    print(json.dumps(result["primary"], indent=2))


if __name__ == "__main__":
    main()
