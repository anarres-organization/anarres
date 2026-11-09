#!/usr/bin/env python3
"""Reproduce the grouped retrospective finance intervention audit."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "panels.json"
SOURCES = ROOT / "SOURCES.json"
OUT = ROOT / "results"
FEATURES = [
    "quality_control",
    "retention_control",
    "verifier_alignment",
    "policy_relative_difficulty",
    "out_of_domain_mix",
    "raw_volume_only",
    "sft_stage",
    "rl_stage",
    "data_fraction",
]


def solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Solve a dense linear system with deterministic pivoting."""
    n = len(vector)
    augmented = [matrix[i][:] + [vector[i]] for i in range(n)]
    for column in range(n):
        pivot = max(range(column, n), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("singular system")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(n):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                augmented[row][j] - factor * augmented[column][j] for j in range(n + 1)
            ]
    return [augmented[i][-1] for i in range(n)]


def ridge_fit(xs: list[list[float]], ys: list[float], penalty: float = 1.0) -> list[float]:
    width = len(xs[0]) + 1
    gram = [[0.0] * width for _ in range(width)]
    rhs = [0.0] * width
    for x, y in zip(xs, ys, strict=True):
        row = [1.0] + x
        for i in range(width):
            rhs[i] += row[i] * y
            for j in range(width):
                gram[i][j] += row[i] * row[j]
    for i in range(1, width):
        gram[i][i] += penalty
    return solve(gram, rhs)


def ridge_predict(coef: list[float], x: list[float]) -> float:
    return coef[0] + sum(weight * value for weight, value in zip(coef[1:], x, strict=True))


def quality_rule(x: list[float]) -> float:
    values = dict(zip(FEATURES, x, strict=True))
    return (
        2.0 * values["quality_control"]
        + 1.5 * values["retention_control"]
        + values["verifier_alignment"]
        + values["policy_relative_difficulty"]
        - values["out_of_domain_mix"]
        - values["raw_volume_only"]
    )


def training_rule(x: list[float]) -> float:
    values = dict(zip(FEATURES, x, strict=True))
    return values["sft_stage"] + values["rl_stage"] + values["data_fraction"]


def normalized_rows(document: dict) -> list[dict]:
    rows = []
    for panel in document["panels"]:
        by_id = {arm["id"]: arm for arm in panel["arms"]}
        baseline_score = by_id[panel["baseline"]]["score"]
        deltas = [arm["score"] - baseline_score for arm in panel["arms"]]
        scale = max(abs(value) for value in deltas) or 1.0
        for arm, delta in zip(panel["arms"], deltas, strict=True):
            rows.append(
                {
                    "study_id": panel["study_id"],
                    "panel_id": panel["panel_id"],
                    "arm_id": arm["id"],
                    "score": arm["score"],
                    "normalized_utility": delta / scale,
                    "features": arm["features"],
                }
            )
    return rows


def grouped_predictions(rows: list[dict]) -> dict[str, dict[str, float]]:
    predictions = {"ridge": {}, "quality_rule": {}, "more_training": {}}
    studies = sorted({row["study_id"] for row in rows})
    for held_out in studies:
        train = [row for row in rows if row["study_id"] != held_out]
        test = [row for row in rows if row["study_id"] == held_out]
        coef = ridge_fit(
            [row["features"] for row in train],
            [row["normalized_utility"] for row in train],
        )
        for row in test:
            key = f"{row['panel_id']}::{row['arm_id']}"
            predictions["ridge"][key] = ridge_predict(coef, row["features"])
            predictions["quality_rule"][key] = quality_rule(row["features"])
            predictions["more_training"][key] = training_rule(row["features"])
    return predictions


def score_model(rows: list[dict], predictions: dict[str, float]) -> dict:
    panels: dict[str, list[dict]] = {}
    for row in rows:
        panels.setdefault(row["panel_id"], []).append(row)
    squared = []
    pair_correct = 0.0
    pair_total = 0
    regrets = []
    top_correct = 0
    panel_records = []
    for panel_id, panel_rows in sorted(panels.items()):
        for row in panel_rows:
            key = f"{panel_id}::{row['arm_id']}"
            squared.append((predictions[key] - row["normalized_utility"]) ** 2)
        for i, left in enumerate(panel_rows):
            for right in panel_rows[i + 1 :]:
                left_key = f"{panel_id}::{left['arm_id']}"
                right_key = f"{panel_id}::{right['arm_id']}"
                observed = left["normalized_utility"] - right["normalized_utility"]
                predicted = predictions[left_key] - predictions[right_key]
                pair_total += 1
                if observed == 0 or predicted == 0:
                    pair_correct += 0.5
                elif observed * predicted > 0:
                    pair_correct += 1.0
        chosen = max(
            panel_rows,
            key=lambda row: (predictions[f"{panel_id}::{row['arm_id']}"], row["arm_id"]),
        )
        best = max(panel_rows, key=lambda row: (row["normalized_utility"], row["arm_id"]))
        regret = best["normalized_utility"] - chosen["normalized_utility"]
        regrets.append(regret)
        top_correct += chosen["arm_id"] == best["arm_id"]
        panel_records.append(
            {
                "panel_id": panel_id,
                "chosen": chosen["arm_id"],
                "observed_best": best["arm_id"],
                "normalized_regret": round(regret, 6),
            }
        )
    return {
        "normalized_rmse": round(math.sqrt(sum(squared) / len(squared)), 6),
        "pairwise_rank_accuracy": round(pair_correct / pair_total, 6),
        "top_choice_accuracy": round(top_correct / len(panels), 6),
        "mean_normalized_regret": round(sum(regrets) / len(regrets), 6),
        "panels": panel_records,
    }


def main() -> None:
    document = json.loads(DATA.read_text())
    assert document["feature_names"] == FEATURES
    rows = normalized_rows(document)
    predictions = grouped_predictions(rows)
    results = {name: score_model(rows, values) for name, values in predictions.items()}
    summary = {
        "status": "retrospective_exploratory",
        "independent_studies": len({row["study_id"] for row in rows}),
        "decision_panels": len({row["panel_id"] for row in rows}),
        "trained_intervention_rows_including_controls": len(rows),
        "validation": "leave-one-study-out",
        "normalization": (
            "baseline-subtracted utility divided by maximum absolute within-panel change"
        ),
        "models": results,
        "interpretation_guardrails": [
            "all outcomes were public before this feature schema was assembled",
            "targets inside one trained intervention are not independent runs",
            "source-native aggregate outcomes do not identify training-seed variance",
            (
                "the analysis motivates prospective measurements and baselines "
                "but does not validate them"
            ),
        ],
    }
    OUT.mkdir(exist_ok=True)
    output = OUT / "summary.json"
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    manifest = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [DATA, SOURCES, output]
    }
    (OUT / "MANIFEST.sha256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
