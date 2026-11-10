#!/usr/bin/env python3
"""Score the released finance adaptive-environment decision bridge."""

from __future__ import annotations

import hashlib
import json
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "panels.json"
OUT = ROOT / "results" / "summary.json"
MANIFEST = ROOT / "MANIFEST.sha256.json"


def solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [matrix[index][:] + [vector[index]] for index in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("singular system")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                augmented[row][index] - factor * augmented[column][index]
                for index in range(size + 1)
            ]
    return [augmented[index][-1] for index in range(size)]


def ridge_fit(xs: list[list[float]], ys: list[float], penalty: float = 4.0) -> list[float]:
    width = len(xs[0]) + 1
    gram = [[0.0] * width for _ in range(width)]
    rhs = [0.0] * width
    for features, outcome in zip(xs, ys, strict=True):
        row = [1.0] + features
        for left in range(width):
            rhs[left] += row[left] * outcome
            for right in range(width):
                gram[left][right] += row[left] * row[right]
    for index in range(1, width):
        gram[index][index] += penalty
    return solve(gram, rhs)


def normalize_panel(panel: dict) -> list[dict]:
    utilities = [arm["utility"] for arm in panel["arms"]]
    low, high = min(utilities), max(utilities)
    span = high - low
    return [
        {
            **arm,
            "source_id": panel["source_id"],
            "panel_id": panel["panel_id"],
            "baseline": panel["baseline"],
            "normalized_utility": (arm["utility"] - low) / span if span else 0.5,
        }
        for arm in panel["arms"]
    ]


def score_method(panels: list[dict], predictions: dict[str, float]) -> dict:
    pair_correct = 0.0
    pair_total = 0
    top_correct = 0
    regrets = []
    decisions = []
    for panel in panels:
        rows = normalize_panel(panel)
        for left, right in combinations(rows, 2):
            left_prediction = predictions[f"{panel['panel_id']}::{left['id']}"]
            right_prediction = predictions[f"{panel['panel_id']}::{right['id']}"]
            observed_delta = left["utility"] - right["utility"]
            predicted_delta = left_prediction - right_prediction
            if observed_delta == 0 or predicted_delta == 0:
                pair_correct += 0.5
            elif (observed_delta > 0) == (predicted_delta > 0):
                pair_correct += 1.0
            pair_total += 1
        selected = max(
            rows,
            key=lambda row: (predictions[f"{panel['panel_id']}::{row['id']}"], row["id"]),
        )
        best = max(rows, key=lambda row: (row["utility"], row["id"]))
        top_correct += selected["id"] == best["id"]
        regret = best["normalized_utility"] - selected["normalized_utility"]
        regrets.append(regret)
        decisions.append(
            {
                "panel_id": panel["panel_id"],
                "selected": selected["id"],
                "observed_best": best["id"],
                "normalized_regret": round(regret, 6),
            }
        )
    return {
        "pairwise_ordering": round(pair_correct / pair_total, 6),
        "top_choice_accuracy": round(top_correct / len(panels), 6),
        "mean_normalized_regret": round(sum(regrets) / len(regrets), 6),
        "pairwise_comparisons": pair_total,
        "panels": len(panels),
        "decisions": decisions,
    }


def practical_predictions(document: dict) -> dict[str, float]:
    weights = [document["feature_rule"][name] for name in document["feature_names"]]
    return {
        f"{panel['panel_id']}::{arm['id']}": sum(
            weight * value for weight, value in zip(weights, arm["features"], strict=True)
        )
        for panel in document["panels"]
        for arm in panel["arms"]
    }


def ridge_predictions(document: dict) -> dict[str, float]:
    sources = sorted({panel["source_id"] for panel in document["panels"]})
    predictions = {}
    for heldout in sources:
        training = [
            row
            for panel in document["panels"]
            if panel["source_id"] != heldout
            for row in normalize_panel(panel)
        ]
        coefficients = ridge_fit(
            [row["features"] for row in training],
            [row["normalized_utility"] for row in training],
        )
        for panel in document["panels"]:
            if panel["source_id"] != heldout:
                continue
            for arm in panel["arms"]:
                predictions[f"{panel['panel_id']}::{arm['id']}"] = coefficients[0] + sum(
                    coefficient * value
                    for coefficient, value in zip(coefficients[1:], arm["features"], strict=True)
                )
    return predictions


def baseline_predictions(document: dict) -> dict[str, float]:
    return {
        f"{panel['panel_id']}::{arm['id']}": float(arm["id"] != panel["baseline"])
        for panel in document["panels"]
        for arm in panel["arms"]
    }


def guardrail_audit(document: dict, practical: dict[str, float]) -> dict:
    panels = []
    for panel in document["panels"]:
        rows = panel["arms"]
        guardrail = next(
            (
                field
                for field in ("protected_regressions", "unauthorized_state", "compliance_issues")
                if all(field in row for row in rows)
            ),
            None,
        )
        if guardrail is None:
            continue
        selected = max(rows, key=lambda row: practical[f"{panel['panel_id']}::{row['id']}"])
        baseline = next(row for row in rows if row["id"] == panel["baseline"])
        blocked = selected[guardrail] > baseline[guardrail]
        panels.append(
            {
                "panel_id": panel["panel_id"],
                "guardrail": guardrail,
                "selected": selected["id"],
                "selected_value": selected[guardrail],
                "baseline_value": baseline[guardrail],
                "decision": "block" if blocked else "eligible",
            }
        )
    return {
        "panels_with_comparable_guardrail": len(panels),
        "blocked_decisions": sum(row["decision"] == "block" for row in panels),
        "decisions": panels,
    }


def main() -> None:
    document = json.loads(DATA.read_text())
    practical = practical_predictions(document)
    ridge = ridge_predictions(document)
    update = baseline_predictions(document)
    output = {
        "schema_version": 1,
        "status": "RETROSPECTIVE_PRIMARY_SOURCE_BRIDGE",
        "support": {
            "sources": len({panel["source_id"] for panel in document["panels"]}),
            "panels": len(document["panels"]),
            "arms": sum(len(panel["arms"]) for panel in document["panels"]),
        },
        "evaluations": {
            "fixed_practical_rule": score_method(document["panels"], practical),
            "leave_one_source_out_ridge": score_method(document["panels"], ridge),
            "always_update": score_method(document["panels"], update),
        },
        "guardrail_audit": guardrail_audit(document, practical),
        "interpretation": [
            "outcomes were public before this bridge and the feature representation was "
            "designed with access to the source papers",
            "complete source holdout tests coefficient transfer but does not make this a "
            "prospective result",
            "source-native utilities are normalized only within matched decision panels",
            "capability and guardrail outcomes remain separate and a guardrail regression "
            "blocks promotion",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    files = {
        "README.md": ROOT / "README.md",
        "PROTOCOL.json": ROOT / "PROTOCOL.json",
        "SOURCES.json": ROOT / "SOURCES.json",
        "data/panels.json": DATA,
        "scripts/score_bridge.py": Path(__file__),
        "results/summary.json": OUT,
    }
    manifest = {
        label: hashlib.sha256(path.read_bytes()).hexdigest() for label, path in files.items()
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
