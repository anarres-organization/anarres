#!/usr/bin/env python3
"""Reproduce the compact hidden-run risk audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path

MODELS = ("claude-3-7-sonnet", "gpt-4.1", "gpt-4.1-mini", "o4-mini")
TRAIN_MODELS = MODELS[:3]


def auc(scores: list[float], labels: list[int]) -> float:
    ordered = sorted(zip(scores, labels, strict=True), key=lambda item: item[0])
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        raise ValueError("AUC requires both classes")
    positive_rank_sum = 0.0
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][0] == ordered[index][0]:
            end += 1
        average_rank = ((index + 1) + end) / 2.0
        positive_rank_sum += average_rank * sum(label for _, label in ordered[index:end])
        index = end
    return (positive_rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def canonical_digest(value: object) -> str:
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return hashlib.sha256(payload).hexdigest()


def close(actual: float, expected: float, tolerance: float = 1e-12) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{actual} != {expected}")


def indexed(compact: dict) -> dict:
    result = {}
    for record in compact["records"]:
        result[(record["domain"], record["model"])] = {
            row["task_id"]: row for row in record["tasks"]
        }
    return result


def top_capture(scores: dict[str, float], tasks: dict[str, dict]) -> float:
    count = max(1, math.ceil(0.20 * len(scores)))
    selected = sorted(scores, key=lambda task_id: (-scores[task_id], task_id))[:count]
    total_failures = sum(1 - reward for row in tasks.values() for reward in row["rewards"])
    selected_failures = sum(
        1 - reward for task_id in selected for reward in tasks[task_id]["rewards"]
    )
    return selected_failures / total_failures


def reproduce_development(data: dict, released: dict) -> None:
    folds = []
    for domain in ("airline", "retail"):
        task_sets = {tuple(sorted(data[(domain, model)])) for model in MODELS}
        if len(task_sets) != 1:
            raise AssertionError(f"task membership differs in {domain}")
        task_ids = list(next(iter(task_sets)))
        for held_out_model in MODELS:
            held_out = data[(domain, held_out_model)]
            training_models = [model for model in MODELS if model != held_out_model]
            history_risk = {
                task_id: 1.0
                - sum(sum(data[(domain, model)][task_id]["rewards"]) for model in training_models)
                / 12.0
                for task_id in task_ids
            }
            scores, action_scores, labels = [], [], []
            max_actions = max(row["required_action_count"] for row in held_out.values()) or 1
            for task_id in task_ids:
                for reward in held_out[task_id]["rewards"]:
                    scores.append(history_risk[task_id])
                    action_scores.append(held_out[task_id]["required_action_count"] / max_actions)
                    labels.append(1 - reward)
            constant = sum(scores) / len(scores)
            folds.append(
                {
                    "pass_error": abs((1.0 - constant) - (1.0 - sum(labels) / len(labels))),
                    "history_auc": auc(scores, labels),
                    "action_auc": auc(action_scores, labels),
                    "history_brier": sum(
                        (score - label) ** 2 for score, label in zip(scores, labels, strict=True)
                    )
                    / len(labels),
                    "constant_brier": sum((constant - label) ** 2 for label in labels)
                    / len(labels),
                    "history_capture": top_capture(history_risk, held_out),
                    "action_capture": top_capture(
                        {
                            task_id: float(held_out[task_id]["required_action_count"])
                            for task_id in task_ids
                        },
                        held_out,
                    ),
                    "attempts": len(labels),
                }
            )
    summary = released["summary"]
    close(
        sum(row["pass_error"] for row in folds) / len(folds),
        summary["mean_absolute_pass_rate_error"],
    )
    close(
        sum(row["history_auc"] for row in folds) / len(folds), summary["mean_history_failure_auc"]
    )
    close(sum(row["action_auc"] for row in folds) / len(folds), summary["mean_action_count_auc"])
    close(
        sum(row["history_brier"] for row in folds) / len(folds),
        summary["mean_history_failure_brier"],
    )
    close(sum(row["constant_brier"] for row in folds) / len(folds), summary["mean_constant_brier"])
    close(
        sum(row["history_capture"] for row in folds) / len(folds),
        summary["mean_history_top20_failure_capture"],
    )
    close(
        sum(row["action_capture"] for row in folds) / len(folds),
        summary["mean_action_top20_failure_capture"],
    )
    if sum(row["attempts"] for row in folds) != summary["task_model_attempts"]:
        raise AssertionError("development attempt count mismatch")


def validate_freeze(data: dict, frozen: dict) -> None:
    embedded = frozen["freeze_sha256"]
    without_digest = dict(frozen)
    del without_digest["freeze_sha256"]
    if canonical_digest(without_digest) != embedded:
        raise AssertionError("frozen prediction digest mismatch")
    telecom_tasks = data[("telecom", "gpt-4.1")]
    predictions = {row["task_id"]: row for row in frozen["predictions"]}
    if set(predictions) != set(telecom_tasks):
        raise AssertionError("frozen telecom membership mismatch")
    for task_id, row in predictions.items():
        attempts = [
            reward
            for model in TRAIN_MODELS
            for reward in data[("telecom", model)][task_id]["rewards"]
        ]
        close(row["predicted_failure_probability"], 1.0 - sum(attempts) / len(attempts))
        if row["required_action_count"] != telecom_tasks[task_id]["required_action_count"]:
            raise AssertionError("action count mismatch")


def score_target(data: dict, frozen: dict, released: dict) -> tuple[list[str], dict[str, float]]:
    target = data[("telecom", "o4-mini")]
    predictions = {row["task_id"]: row for row in frozen["predictions"]}
    scores, action_scores, labels = [], [], []
    for task_id in sorted(target):
        for reward in target[task_id]["rewards"]:
            scores.append(predictions[task_id]["predicted_failure_probability"])
            action_scores.append(float(target[task_id]["required_action_count"]))
            labels.append(1 - reward)
    observed_pass = 1.0 - sum(labels) / len(labels)
    constant = 1.0 - frozen["predicted_pass_rate"]
    computed = {
        "observed_pass_rate": observed_pass,
        "absolute_pass_rate_error": abs(frozen["predicted_pass_rate"] - observed_pass),
        "task_failure_auc": auc(scores, labels),
        "required_action_count_auc": auc(action_scores, labels),
        "task_failure_brier": sum(
            (score - label) ** 2 for score, label in zip(scores, labels, strict=True)
        )
        / len(labels),
        "constant_brier": sum((constant - label) ** 2 for label in labels) / len(labels),
    }
    for name, value in computed.items():
        close(value, released[name])
    return sorted(target), computed


def percentile(values: list[float], probability: float) -> float:
    values = sorted(values)
    position = probability * (len(values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    weight = position - lower
    return values[lower] * (1.0 - weight) + values[upper] * weight


def validate_bootstrap(data: dict, frozen: dict, released: dict) -> None:
    target = data[("telecom", "o4-mini")]
    predictions = {row["task_id"]: row for row in frozen["predictions"]}
    task_ids = sorted(target)
    constant = 1.0 - frozen["predicted_pass_rate"]
    rng = random.Random(released["seed"])
    distributions = {
        name: [] for name in ("history_auc", "action_auc", "auc_delta", "brier_improvement")
    }
    while len(distributions["history_auc"]) < released["samples"]:
        sampled = [rng.choice(task_ids) for _ in task_ids]
        labels, history_scores, action_scores = [], [], []
        for task_id in sampled:
            task_labels = [1 - reward for reward in target[task_id]["rewards"]]
            labels.extend(task_labels)
            history_scores.extend([predictions[task_id]["predicted_failure_probability"]] * 4)
            action_scores.extend([float(target[task_id]["required_action_count"])] * 4)
        history_auc = auc(history_scores, labels)
        action_auc = auc(action_scores, labels)
        history_brier = sum(
            (score - label) ** 2 for score, label in zip(history_scores, labels, strict=True)
        ) / len(labels)
        constant_brier = sum((constant - label) ** 2 for label in labels) / len(labels)
        distributions["history_auc"].append(history_auc)
        distributions["action_auc"].append(action_auc)
        distributions["auc_delta"].append(history_auc - action_auc)
        distributions["brier_improvement"].append(constant_brier - history_brier)
    for name, values in distributions.items():
        expected = released["intervals"][name]
        close(percentile(values, 0.025), expected["lower_95"])
        close(percentile(values, 0.5), expected["median"])
        close(percentile(values, 0.975), expected["upper_95"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-dir", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    study = args.study_dir.resolve()
    compact = json.loads((study / "data/compact-outcomes.json").read_text())
    data = indexed(compact)
    development = json.loads((study / "results/DEVELOPMENT_AUDIT.json").read_text())
    frozen = json.loads((study / "results/FROZEN_PREDICTION.json").read_text())
    scored = json.loads((study / "results/SCORED_TARGET.json").read_text())
    bootstrap = json.loads((study / "results/BOOTSTRAP.json").read_text())
    reproduce_development(data, development)
    validate_freeze(data, frozen)
    task_ids, computed = score_target(data, frozen, scored)
    validate_bootstrap(data, frozen, bootstrap)
    print(
        json.dumps(
            {
                "status": "reproduced",
                "development_folds": development["summary"]["fold_count"],
                "frozen_target_tasks": len(task_ids),
                "task_failure_auc": computed["task_failure_auc"],
                "absolute_pass_rate_error": computed["absolute_pass_rate_error"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
