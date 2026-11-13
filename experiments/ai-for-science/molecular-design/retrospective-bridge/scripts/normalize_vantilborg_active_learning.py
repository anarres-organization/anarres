#!/usr/bin/env python3
"""Normalize the van Tilborg active-learning panel and run held-out-library audits."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

PRIMARY_DATASETS = ("ALDH1", "PKM2", "VDR")
EXPECTED_SHA256 = "646a4b499ebcb0ad2681ebee708bc61f69cd47fee1674b3d6ebaedc9256dc8f0"
ALPHAS = (0.1, 1.0, 10.0, 100.0)
OPERATIONAL_FEATURES = (
    "cum_hits_discovered_initial",
    "train_roc_auc",
    "train_balanced_accuracy",
)
GRAPH_FEATURES = (
    "n_unique_scaffolds",
    "mean_total_sims",
    "mean_tani_per_batch",
    "mean_tani_batch_to_start_batch",
    "unique_patterns",
)
FEATURE_SETS = {
    "method_only": (),
    "method_by_architecture": ("architecture",),
    "operational": ("architecture", *OPERATIONAL_FEATURES),
    "graph": ("architecture", *GRAPH_FEATURES),
    "combined": ("architecture", *OPERATIONAL_FEATURES, *GRAPH_FEATURES),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_float(value: str) -> float:
    if value == "" or value.lower() in {"na", "nan"}:
        return math.nan
    return float(value)


def read_runs(path: Path) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, int], list[dict[str, str]]] = defaultdict(list)
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row["dataset"] not in PRIMARY_DATASETS:
                continue
            # The released table repeats RF runs for a scrambling audit. The
            # canonical records have no explicit scrambling field.
            if row["architecture"] == "rf" and row["scrambledx"].lower() not in {
                "",
                "na",
                "nan",
            }:
                continue
            key = (
                row["dataset"],
                row["architecture"],
                row["acquisition_method"],
                int(row["seed"]),
            )
            grouped[key].append(row)

    runs = []
    for (dataset, architecture, method, seed), rows in sorted(grouped.items()):
        rows.sort(key=lambda row: int(row["screen_cycle"]))
        first = rows[0]
        last = rows[-1]
        runs.append(
            {
                "dataset": dataset,
                "architecture": architecture,
                "method": method,
                "seed": seed,
                "initial_cycle": int(first["screen_cycle"]),
                "terminal_cycle": int(last["screen_cycle"]),
                "terminal_hits": int(last["cum_hits_discovered"]),
                "cum_hits_discovered_initial": float(first["cum_hits_discovered"]),
                "train_roc_auc": parse_float(first["train_roc_auc"]),
                "train_balanced_accuracy": parse_float(first["train_balanced_accuracy"]),
                "n_unique_scaffolds": parse_float(first["n_unique_scaffolds"]),
                "mean_total_sims": parse_float(first["mean_total_sims"]),
                "mean_tani_per_batch": parse_float(first["mean_tani_per_batch"]),
                "mean_tani_batch_to_start_batch": parse_float(
                    first["mean_tani_batch_to_start_batch"]
                ),
                "unique_patterns": parse_float(first["unique_patterns"]),
            }
        )
    return runs


def aggregate_conditions(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in runs:
        grouped[(row["dataset"], row["architecture"], row["method"])].append(row)

    methods = sorted({row["method"] for row in runs})
    records = []
    contexts: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for (dataset, architecture, method), rows in sorted(grouped.items()):
        record = {
            "dataset": dataset,
            "architecture": architecture,
            "method": method,
            "seeds": len(rows),
            "terminal_hits_mean": mean(row["terminal_hits"] for row in rows),
            "terminal_cycle_min": min(row["terminal_cycle"] for row in rows),
            "terminal_cycle_max": max(row["terminal_cycle"] for row in rows),
        }
        for feature in (*OPERATIONAL_FEATURES, *GRAPH_FEATURES):
            values = [row[feature] for row in rows]
            if any(not math.isfinite(value) for value in values):
                raise ValueError(f"non-finite {feature} for {(dataset, architecture, method)}")
            record[feature] = mean(values)
        contexts[(dataset, architecture)].append(record)

    for context, rows in sorted(contexts.items()):
        if sorted(row["method"] for row in rows) != methods:
            raise ValueError(f"incomplete candidate set for {context}")
        if min(row["seeds"] for row in rows) < 5:
            raise ValueError(f"insufficient repeated runs for {context}")
        low = min(row["terminal_hits_mean"] for row in rows)
        high = max(row["terminal_hits_mean"] for row in rows)
        for row in rows:
            row["normalized_utility"] = (
                (row["terminal_hits_mean"] - low) / (high - low) if high > low else 0.5
            )
            records.append(row)
    return records


def standardize(
    rows: list[dict[str, Any]],
    features: tuple[str, ...],
    state: dict[str, tuple[float, float]] | None,
) -> tuple[list[list[float]], dict[str, tuple[float, float]]]:
    continuous = tuple(feature for feature in features if feature != "architecture")
    if state is None:
        state = {}
        for feature in continuous:
            values = [float(row[feature]) for row in rows]
            center = mean(values)
            variance = mean((value - center) ** 2 for value in values)
            state[feature] = (center, math.sqrt(variance) or 1.0)
    values = []
    for row in rows:
        values.append(
            [
                (float(row[feature]) - state[feature][0]) / state[feature][1]
                for feature in continuous
            ]
        )
    return values, state


def design(
    rows: list[dict[str, Any]],
    features: tuple[str, ...],
    methods: list[str],
    architectures: list[str],
    state: dict[str, tuple[float, float]] | None = None,
) -> tuple[list[list[float]], dict[str, tuple[float, float]]]:
    continuous, state = standardize(rows, features, state)
    contexts = []
    for row, values in zip(rows, continuous, strict=True):
        if "architecture" in features:
            values = values + [float(row["architecture"] == name) for name in architectures]
        contexts.append(values)

    matrix = []
    for row, context in zip(rows, contexts, strict=True):
        method = [float(row["method"] == name) for name in methods]
        interactions = [value * coordinate for value in method for coordinate in context]
        matrix.append(method + interactions)
    return matrix, state


def solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    augmented = [row[:] + [value] for row, value in zip(matrix, vector, strict=True)]
    size = len(augmented)
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("singular ridge system")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor:
                augmented[row] = [
                    left - factor * right
                    for left, right in zip(augmented[row], augmented[column], strict=True)
                ]
    return [row[-1] for row in augmented]


def ridge_predict(
    train_x: list[list[float]], train_y: list[float], test_x: list[list[float]], alpha: float
) -> list[float]:
    width = len(train_x[0])
    x_means = [mean(row[column] for row in train_x) for column in range(width)]
    y_mean = mean(train_y)
    centered_x = [[value - x_means[i] for i, value in enumerate(row)] for row in train_x]
    centered_y = [value - y_mean for value in train_y]
    gram = [[0.0] * width for _ in range(width)]
    target = [0.0] * width
    for row, outcome in zip(centered_x, centered_y, strict=True):
        for left in range(width):
            target[left] += row[left] * outcome
            for right in range(width):
                gram[left][right] += row[left] * row[right]
    for index in range(width):
        gram[index][index] += alpha
    coefficients = solve(gram, target)
    intercept = y_mean - sum(
        value * coefficient for value, coefficient in zip(x_means, coefficients, strict=True)
    )
    return [
        intercept
        + sum(value * coefficient for value, coefficient in zip(row, coefficients, strict=True))
        for row in test_x
    ]


def score(rows: list[dict[str, Any]], predictions: list[float]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[tuple[dict[str, Any], float]]] = defaultdict(list)
    for row, prediction in zip(rows, predictions, strict=True):
        grouped[(row["dataset"], row["architecture"])].append((row, prediction))

    credits = []
    regrets = []
    selections = []
    for (dataset, architecture), items in sorted(grouped.items()):
        for left, right in itertools.combinations(items, 2):
            observed = math.copysign(
                1, left[0]["normalized_utility"] - right[0]["normalized_utility"]
            )
            predicted = math.copysign(1, left[1] - right[1])
            observed_tie = left[0]["normalized_utility"] == right[0]["normalized_utility"]
            predicted_tie = left[1] == right[1]
            credits.append(0.5 if observed_tie or predicted_tie else float(observed == predicted))
        selected = max(items, key=lambda item: (item[1], item[0]["method"]))
        best = max(item[0]["normalized_utility"] for item in items)
        regret = best - selected[0]["normalized_utility"]
        regrets.append(regret)
        selections.append(
            {
                "dataset": dataset,
                "architecture": architecture,
                "selected_method": selected[0]["method"],
                "observed_best_methods": sorted(
                    item[0]["method"] for item in items if item[0]["normalized_utility"] == best
                ),
                "normalized_regret": regret,
            }
        )
    return {
        "pairwise_ordering": mean(credits),
        "mean_normalized_regret": mean(regrets),
        "best_method_credit": mean(
            float(row["selected_method"] in row["observed_best_methods"]) for row in selections
        ),
        "contexts": len(selections),
        "selections": selections,
    }


def nested_leave_one_dataset_out(
    records: list[dict[str, Any]], features: tuple[str, ...]
) -> dict[str, Any]:
    methods = sorted({row["method"] for row in records})
    architectures = sorted({row["architecture"] for row in records})
    predictions = []
    held_out_rows = []
    chosen_alphas = {}
    for held_out in PRIMARY_DATASETS:
        train = [row for row in records if row["dataset"] != held_out]
        test = [row for row in records if row["dataset"] == held_out]
        candidates = []
        for alpha in ALPHAS:
            validation_rows = []
            validation_predictions = []
            for validation_dataset in sorted({row["dataset"] for row in train}):
                inner_train = [row for row in train if row["dataset"] != validation_dataset]
                validation = [row for row in train if row["dataset"] == validation_dataset]
                train_x, state = design(inner_train, features, methods, architectures)
                validation_x, _ = design(validation, features, methods, architectures, state)
                validation_predictions.extend(
                    ridge_predict(
                        train_x,
                        [row["normalized_utility"] for row in inner_train],
                        validation_x,
                        alpha,
                    )
                )
                validation_rows.extend(validation)
            candidates.append(
                (score(validation_rows, validation_predictions)["mean_normalized_regret"], alpha)
            )
        alpha = min(candidates)[1]
        chosen_alphas[held_out] = alpha
        train_x, state = design(train, features, methods, architectures)
        test_x, _ = design(test, features, methods, architectures, state)
        predictions.extend(
            ridge_predict(
                train_x,
                [row["normalized_utility"] for row in train],
                test_x,
                alpha,
            )
        )
        held_out_rows.extend(test)
    result = score(held_out_rows, predictions)
    result["chosen_alpha_by_held_out_dataset"] = chosen_alphas
    return result


def fixed_method_baseline(records: list[dict[str, Any]]) -> dict[str, Any]:
    predictions = []
    held_out_rows = []
    for held_out in PRIMARY_DATASETS:
        train = [row for row in records if row["dataset"] != held_out]
        test = [row for row in records if row["dataset"] == held_out]
        priors = {
            method: mean(row["normalized_utility"] for row in train if row["method"] == method)
            for method in sorted({row["method"] for row in train})
        }
        predictions.extend(priors[row["method"]] for row in test)
        held_out_rows.extend(test)
    return score(held_out_rows, predictions)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    digest = sha256(args.source_csv)
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"source table digest mismatch: {digest}")

    runs = read_runs(args.source_csv)
    records = aggregate_conditions(runs)
    audits = {
        name: nested_leave_one_dataset_out(records, features)
        for name, features in FEATURE_SETS.items()
    }
    output = {
        "schema_version": "anarres.molecular.vantilborg_active_learning_bridge.v1",
        "study": "Traversing Chemical Space with Active Deep Learning for Low-data Drug Discovery",
        "evidence_tier": "retrospective_cross_dataset_decision_audit",
        "source_sha256": digest,
        "claim_boundary": (
            "The audit predicts acquisition-method choices for held-out molecular libraries from "
            "published active-learning simulations. It does not use prospective wet-lab outcomes "
            "and is not a pre-training RxnFlow profile result."
        ),
        "support": {
            "primary_datasets": list(PRIMARY_DATASETS),
            "architectures": sorted({row["architecture"] for row in records}),
            "acquisition_methods": sorted({row["method"] for row in records}),
            "contexts": len({(row["dataset"], row["architecture"]) for row in records}),
            "condition_records": len(records),
            "run_records": len(runs),
            "minimum_seeds_per_condition": min(row["seeds"] for row in records),
        },
        "leave_one_dataset_out": audits,
        "training_fold_fixed_method": fixed_method_baseline(records),
        "condition_records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
