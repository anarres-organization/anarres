"""Evaluate charged early-measurement decisions on released PMO trajectories."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

PILOT_BUDGETS = (1000, 2500, 5000, 7500)
FINAL_BUDGET = 10000
WEIGHT_GRID = tuple(
    (a / 4, b / 4, c / 4) for a in range(5) for b in range(5 - a) for c in (4 - a - b,)
)
BOOTSTRAP_SEED = 20261111
PAIRING_REPEATS = 1000


def canonical(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 12)
    if isinstance(value, list):
        return [canonical(item) for item in value]
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in value.items()}
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rank01(values: dict[str, float]) -> dict[str, float]:
    unique = sorted(set(values.values()))
    denominator = max(len(unique) - 1, 1)
    lookup = {value: index / denominator for index, value in enumerate(unique)}
    return {key: lookup[value] for key, value in values.items()}


def normalize(values: dict[str, float]) -> dict[str, float]:
    low = min(values.values())
    high = max(values.values())
    denominator = max(high - low, 1e-12)
    return {key: (value - low) / denominator for key, value in values.items()}


def mean_records(
    records: list[dict[str, Any]],
) -> tuple[dict[tuple[str, str, int], dict[str, float]], dict[tuple[str, str], int]]:
    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    runs: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in records:
        key = (row["task"], row["method"], row["oracle_budget"])
        grouped[key].append(row)
        runs[(row["task"], row["method"])].add(row["run_label"])
    aggregates = {}
    for key, rows in grouped.items():
        aggregates[key] = {
            field: mean(float(row[field]) for row in rows)
            for field in ("auc_top10", "endpoint_top10", "observed_unique_molecules")
        }
    return aggregates, {key: len(labels) for key, labels in runs.items()}


def task_panel(
    aggregates: dict[tuple[str, str, int], dict[str, float]],
    task: str,
    methods: list[str],
    pilot_budget: int,
) -> dict[str, dict[str, float]]:
    final = {method: aggregates[(task, method, FINAL_BUDGET)]["auc_top10"] for method in methods}
    pilot_auc = {
        method: aggregates[(task, method, pilot_budget)]["auc_top10"] for method in methods
    }
    endpoint = {
        method: aggregates[(task, method, pilot_budget)]["endpoint_top10"] for method in methods
    }
    unique_fraction = {
        method: min(
            aggregates[(task, method, pilot_budget)]["observed_unique_molecules"] / pilot_budget,
            1.0,
        )
        for method in methods
    }
    return {
        "final": final,
        "normalized_final": normalize(final),
        "pilot_auc_rank": rank01(pilot_auc),
        "endpoint_rank": rank01(endpoint),
        "unique_fraction_rank": rank01(unique_fraction),
    }


def score_panel(final: dict[str, float], prediction: dict[str, float]) -> dict[str, float]:
    maximum = max(prediction.values())
    selected = sorted(
        method for method, value in prediction.items() if abs(value - maximum) <= 1e-12
    )
    best = max(final.values())
    selected_utility = mean(final[method] for method in selected)
    best_methods = {method for method, value in final.items() if abs(value - best) <= 1e-12}
    top_credit = sum(method in best_methods for method in selected) / len(selected)
    correct = 0.0
    total = 0
    methods = sorted(final)
    for left, right in itertools.combinations(methods, 2):
        observed = final[left] - final[right]
        if abs(observed) <= 1e-12:
            continue
        predicted = prediction[left] - prediction[right]
        total += 1
        if abs(predicted) <= 1e-12:
            correct += 0.5
        elif predicted * observed > 0:
            correct += 1.0
    return {
        "top_choice_credit": top_credit,
        "normalized_regret": best - selected_utility,
        "pairwise_ordering": correct / total,
        "selected_count": len(selected),
    }


def selected_methods(prediction: dict[str, float]) -> list[str]:
    maximum = max(prediction.values())
    return sorted(method for method, value in prediction.items() if abs(value - maximum) <= 1e-12)


def macro(panel_scores: list[dict[str, float]]) -> dict[str, float]:
    return {
        key: mean(float(row[key]) for row in panel_scores)
        for key in (
            "top_choice_credit",
            "normalized_regret",
            "auc_top10_regret",
            "pairwise_ordering",
        )
    }


def score_prediction(
    panel: dict[str, dict[str, float]], prediction: dict[str, float]
) -> dict[str, float]:
    result = score_panel(panel["normalized_final"], prediction)
    result["auc_top10_regret"] = score_panel(panel["final"], prediction)["normalized_regret"]
    return result


def convex_prediction(
    panel: dict[str, dict[str, float]], weights: tuple[float, float, float]
) -> dict[str, float]:
    return {
        method: (
            weights[0] * panel["pilot_auc_rank"][method]
            + weights[1] * panel["endpoint_rank"][method]
            + weights[2] * panel["unique_fraction_rank"][method]
        )
        for method in panel["final"]
    }


def select_convex_weights(
    panels: dict[str, dict[str, dict[str, float]]], train_tasks: list[str]
) -> tuple[float, float, float]:
    candidates = []
    for weights in WEIGHT_GRID:
        scores = [
            score_prediction(panels[task], convex_prediction(panels[task], weights))
            for task in train_tasks
        ]
        metrics = macro(scores)
        candidates.append(
            (
                metrics["normalized_regret"],
                -metrics["pairwise_ordering"],
                -metrics["top_choice_credit"],
                weights,
            )
        )
    return min(candidates)[-1]


def method_prior(
    panels: dict[str, dict[str, dict[str, float]]], train_tasks: list[str]
) -> dict[str, float]:
    methods = sorted(next(iter(panels.values()))["final"])
    return {
        method: mean(panels[task]["normalized_final"][method] for task in train_tasks)
        for method in methods
    }


def evaluate_budget(
    aggregates: dict[tuple[str, str, int], dict[str, float]],
    run_counts: dict[tuple[str, str], int],
    tasks: list[str],
    methods: list[str],
    pilot_budget: int,
) -> dict[str, Any]:
    panels = {task: task_panel(aggregates, task, methods, pilot_budget) for task in tasks}
    scores: dict[str, list[dict[str, float]]] = defaultdict(list)
    fold_records = []
    fold_predictions: dict[str, dict[str, dict[str, float]]] = {}
    for task in tasks:
        train_tasks = [other for other in tasks if other != task]
        panel = panels[task]
        weights = select_convex_weights(panels, train_tasks)
        prior = method_prior(panels, train_tasks)
        prior_rank = rank01(prior)
        predictions = {
            "uninformed_tie": {method: 0.0 for method in methods},
            "pilot_auc": panel["pilot_auc_rank"],
            "pilot_endpoint": panel["endpoint_rank"],
            "unique_fraction": panel["unique_fraction_rank"],
            "equal_weight_measurements": convex_prediction(panel, (1 / 3, 1 / 3, 1 / 3)),
            "training_fold_convex": convex_prediction(panel, weights),
            "training_fold_fixed_method": prior_rank,
            "prior_plus_pilot_auc": {
                method: 0.5 * prior_rank[method] + 0.5 * panel["pilot_auc_rank"][method]
                for method in methods
            },
        }
        fold_metrics = {}
        for name, prediction in predictions.items():
            result = score_prediction(panel, prediction)
            scores[name].append(result)
            fold_metrics[name] = result
        fold_predictions[task] = predictions
        pilot_calls = sum(run_counts[(task, method)] * pilot_budget for method in methods)
        primary_selected = selected_methods(predictions["prior_plus_pilot_auc"])
        completion_calls = sum(
            run_counts[(task, method)] * (FINAL_BUDGET - pilot_budget)
            for method in primary_selected
        )
        exhaustive_calls = sum(run_counts[(task, method)] * FINAL_BUDGET for method in methods)
        fold_records.append(
            {
                "held_out_task": task,
                "training_fold_convex_weights": {
                    "pilot_auc": weights[0],
                    "endpoint": weights[1],
                    "unique_fraction": weights[2],
                },
                "primary_rule_selected_methods": primary_selected,
                "selected_methods": {
                    name: selected_methods(prediction) for name, prediction in predictions.items()
                },
                "primary_rule_cost": {
                    "pilot_oracle_calls": pilot_calls,
                    "selected_completion_oracle_calls": completion_calls,
                    "total_oracle_calls": pilot_calls + completion_calls,
                    "exhaustive_oracle_calls": exhaustive_calls,
                    "fraction_of_exhaustive": (pilot_calls + completion_calls) / exhaustive_calls,
                },
                "metrics": fold_metrics,
            }
        )

    metrics = {name: macro(rows) for name, rows in scores.items()}
    task_rows = scores["prior_plus_pilot_auc"]
    rng = random.Random(BOOTSTRAP_SEED + pilot_budget)
    bootstrap = []
    for _ in range(2000):
        sampled = [task_rows[rng.randrange(len(task_rows))] for _ in task_rows]
        bootstrap.append(macro(sampled))
    intervals = {}
    for key in (
        "top_choice_credit",
        "normalized_regret",
        "auc_top10_regret",
        "pairwise_ordering",
    ):
        ordered = sorted(row[key] for row in bootstrap)
        intervals[key] = [ordered[49], ordered[1949]]

    fixed_changes = sum(
        selected_methods(fold_predictions[task]["prior_plus_pilot_auc"])
        != selected_methods(fold_predictions[task]["training_fold_fixed_method"])
        for task in tasks
    )
    pairing_rng = random.Random(BOOTSTRAP_SEED + 10 * pilot_budget)
    pairing_null = []
    for _ in range(PAIRING_REPEATS):
        shuffled_scores = []
        for task in tasks:
            prior = fold_predictions[task]["training_fold_fixed_method"]
            values = list(fold_predictions[task]["pilot_auc"].values())
            pairing_rng.shuffle(values)
            shuffled_auc = dict(zip(methods, values, strict=True))
            prediction = {
                method: 0.5 * prior[method] + 0.5 * shuffled_auc[method] for method in methods
            }
            shuffled_scores.append(score_prediction(panels[task], prediction))
        pairing_null.append(macro(shuffled_scores))
    observed_pairing = metrics["prior_plus_pilot_auc"]
    pairing_control = {
        "repeats": PAIRING_REPEATS,
        "observed": observed_pairing,
        "fraction_null_as_good_or_better_regret": (
            1
            + sum(
                row["normalized_regret"] <= observed_pairing["normalized_regret"]
                for row in pairing_null
            )
        )
        / (PAIRING_REPEATS + 1),
        "fraction_null_as_good_or_better_pairwise_ordering": (
            1
            + sum(
                row["pairwise_ordering"] >= observed_pairing["pairwise_ordering"]
                for row in pairing_null
            )
        )
        / (PAIRING_REPEATS + 1),
    }

    return {
        "pilot_budget_per_method_run": pilot_budget,
        "metrics": metrics,
        "prior_plus_pilot_auc_decisions_different_from_fixed_method": fixed_changes,
        "pilot_pairing_control": pairing_control,
        "primary_rule_task_bootstrap_95_interval": intervals,
        "mean_primary_rule_cost": {
            key: mean(row["primary_rule_cost"][key] for row in fold_records)
            for key in (
                "pilot_oracle_calls",
                "selected_completion_oracle_calls",
                "total_oracle_calls",
                "exhaustive_oracle_calls",
                "fraction_of_exhaustive",
            )
        },
        "folds": fold_records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pmo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = json.loads(args.pmo.read_text())
    aggregates, run_counts = mean_records(payload["records"])
    tasks = sorted({row["task"] for row in payload["records"]})
    methods = sorted({row["method"] for row in payload["records"]})
    results = [
        evaluate_budget(aggregates, run_counts, tasks, methods, pilot_budget)
        for pilot_budget in PILOT_BUDGETS
    ]
    output = {
        "schema_version": "anarres.molecular.pmo_decision_ladder.v1",
        "status": "RETROSPECTIVE_EARLY_OUTCOME_DECISION_AUDIT",
        "claim_boundary": (
            "PMO pilot AUC and endpoint values are early downstream outcomes. This "
            "ladder tests charged temporal selection across held-out oracle tasks. "
            "Prospective RxnFlow environment selection requires measurements made "
            "before target optimization."
        ),
        "source": {
            "name": "Sample Efficiency Matters: A Benchmark for Practical Molecular Optimization",
            "doi": "10.48550/arXiv.2206.12411",
            "pmo_normalized_sha256": sha256(args.pmo),
        },
        "support": {
            "tasks": len(tasks),
            "candidate_methods": len(methods),
            "method_task_pairs": len(tasks) * len(methods),
            "released_runs": sum(run_counts.values()),
            "primary_independent_units": "23 oracle tasks",
            "runs_are_nested_replicates": True,
        },
        "evaluation": {
            "split": "leave-one-oracle-task-out",
            "final_outcome": "mean AUC Top-10 through 10,000 oracle calls",
            "within_task_normalization": "min-max across 25 candidate methods",
            "pilot_measurements": [
                "AUC Top-10 through the pilot budget",
                "endpoint Top-10 at the pilot budget",
                "fraction of the pilot budget producing unique molecules",
            ],
            "cost_contract": (
                "Every released replicate of every candidate is charged through the "
                "pilot budget, followed by completion of the pilot-AUC-selected method."
            ),
        },
        "budget_results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(canonical(output), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
