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


def equivalent(actual: object, expected: object, path: str = "$") -> None:
    if isinstance(actual, bool) or isinstance(expected, bool):
        if actual is not expected:
            raise AssertionError(f"{path}: {actual!r} != {expected!r}")
        return
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        if isinstance(actual, float) or isinstance(expected, float):
            close(float(actual), float(expected))
        elif actual != expected:
            raise AssertionError(f"{path}: {actual!r} != {expected!r}")
        return
    if type(actual) is not type(expected):
        raise AssertionError(f"{path}: type mismatch")
    if isinstance(actual, dict):
        if set(actual) != set(expected):
            raise AssertionError(f"{path}: key mismatch")
        for key in sorted(actual):
            equivalent(actual[key], expected[key], f"{path}.{key}")
        return
    if isinstance(actual, list):
        if len(actual) != len(expected):
            raise AssertionError(f"{path}: length mismatch")
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected, strict=True)):
            equivalent(actual_item, expected_item, f"{path}[{index}]")
        return
    if actual != expected:
        raise AssertionError(f"{path}: {actual!r} != {expected!r}")


def verify_manifest(study: Path) -> None:
    manifest = study / "MANIFEST.sha256"
    listed = {}
    for number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        value, separator, name = line.partition("  ./")
        if not separator or len(value) != 64:
            raise AssertionError(f"manifest line {number} is malformed")
        listed[name] = value
    present = {
        path.relative_to(study).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in study.rglob("*")
        if path.is_file() and path != manifest and "__pycache__" not in path.parts
    }
    if present != listed:
        raise AssertionError("release files do not match MANIFEST.sha256")


def indexed(compact: dict) -> dict:
    result = {}
    for record in compact["records"]:
        result[(record["domain"], record["model"])] = {
            row["task_id"]: row for row in record["tasks"]
        }
    return result


def top_risk(scores: dict[str, float], tasks: dict[str, dict]) -> dict:
    count = max(1, math.ceil(0.20 * len(scores)))
    selected = sorted(scores, key=lambda task_id: (-scores[task_id], task_id))[:count]
    total_failures = sum(1 - reward for row in tasks.values() for reward in row["rewards"])
    selected_failures = sum(
        1 - reward for task_id in selected for reward in tasks[task_id]["rewards"]
    )
    total_attempts = sum(len(row["rewards"]) for row in tasks.values())
    selected_attempts = sum(len(tasks[task_id]["rewards"]) for task_id in selected)
    prevalence = total_failures / total_attempts
    precision = selected_failures / selected_attempts
    return {
        "failure_capture": selected_failures / total_failures,
        "failure_precision": precision,
        "failure_prevalence": prevalence,
        "precision_lift": precision / prevalence,
        "selected_task_count": count,
        "selected_task_ids": selected,
    }


def reproduce_development(data: dict, released: dict) -> None:
    folds = []
    pooled_history_scores, pooled_action_scores, pooled_labels = [], [], []
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
            observed_pass = 1.0 - sum(labels) / len(labels)
            folds.append(
                {
                    "absolute_pass_rate_error": abs((1.0 - constant) - observed_pass),
                    "action_count_auc": auc(action_scores, labels),
                    "action_count_top_risk": top_risk(
                        {
                            task_id: float(held_out[task_id]["required_action_count"])
                            for task_id in task_ids
                        },
                        held_out,
                    ),
                    "constant_brier": sum((constant - label) ** 2 for label in labels)
                    / len(labels),
                    "domain": domain,
                    "held_out_attempt_count": len(labels),
                    "held_out_model": held_out_model,
                    "history_failure_auc": auc(scores, labels),
                    "history_failure_brier": sum(
                        (score - label) ** 2 for score, label in zip(scores, labels, strict=True)
                    )
                    / len(labels),
                    "history_top_risk": top_risk(history_risk, held_out),
                    "observed_pass_rate": observed_pass,
                    "predicted_pass_rate": 1.0 - constant,
                    "task_count": len(task_ids),
                    "task_failure_rmse": math.sqrt(
                        sum(
                            (
                                history_risk[task_id]
                                - (1.0 - sum(held_out[task_id]["rewards"]) / 4.0)
                            )
                            ** 2
                            for task_id in task_ids
                        )
                        / len(task_ids)
                    ),
                    "training_models": training_models,
                }
            )
            pooled_history_scores.extend(scores)
            pooled_action_scores.extend(action_scores)
            pooled_labels.extend(labels)
    equivalent(folds, released["folds"], "$.folds")
    summary = {
        "fold_count": len(folds),
        "mean_absolute_pass_rate_error": sum(row["absolute_pass_rate_error"] for row in folds)
        / len(folds),
        "mean_action_count_auc": sum(row["action_count_auc"] for row in folds) / len(folds),
        "mean_action_top20_failure_capture": sum(
            row["action_count_top_risk"]["failure_capture"] for row in folds
        )
        / len(folds),
        "mean_constant_brier": sum(row["constant_brier"] for row in folds) / len(folds),
        "mean_history_failure_auc": sum(row["history_failure_auc"] for row in folds) / len(folds),
        "mean_history_failure_brier": sum(row["history_failure_brier"] for row in folds)
        / len(folds),
        "mean_history_top20_failure_capture": sum(
            row["history_top_risk"]["failure_capture"] for row in folds
        )
        / len(folds),
        "pooled_action_count_auc": auc(pooled_action_scores, pooled_labels),
        "pooled_history_failure_auc": auc(pooled_history_scores, pooled_labels),
        "task_model_attempts": len(pooled_labels),
    }
    equivalent(summary, released["summary"], "$.summary")


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
    risk = {task_id: row["predicted_failure_probability"] for task_id, row in predictions.items()}
    close(frozen["predicted_pass_rate"], 1.0 - sum(risk.values()) / len(risk))
    expected_top = sorted(risk, key=lambda task_id: (-risk[task_id], task_id))[
        : max(1, math.ceil(0.20 * len(risk)))
    ]
    if frozen["top_risk_task_ids"] != expected_top:
        raise AssertionError("frozen top-risk membership mismatch")


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
    task_scores = {
        task_id: predictions[task_id]["predicted_failure_probability"] for task_id in target
    }
    history_top = top_risk(task_scores, target)
    action_top = top_risk(
        {task_id: float(target[task_id]["required_action_count"]) for task_id in target},
        target,
    )
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
        "failure_prevalence": sum(labels) / len(labels),
        "top20_failure_capture": history_top["failure_capture"],
        "top20_failure_precision": history_top["failure_precision"],
        "top20_precision_lift": history_top["precision_lift"],
        "required_action_top20_failure_capture": action_top["failure_capture"],
        "target_attempt_count": len(labels),
        "task_count": len(target),
    }
    equivalent(computed, {name: released[name] for name in computed}, "$.scored_metrics")
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
        name: []
        for name in (
            "absolute_pass_rate_error",
            "history_auc",
            "action_auc",
            "auc_delta",
            "brier_improvement",
            "top20_failure_capture",
        )
    }
    selected = set(frozen["top_risk_task_ids"])
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
        distributions["absolute_pass_rate_error"].append(abs(constant - sum(labels) / len(labels)))
        distributions["top20_failure_capture"].append(
            sum(
                1 - reward
                for task_id in sampled
                if task_id in selected
                for reward in target[task_id]["rewards"]
            )
            / sum(labels)
        )
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
    verify_manifest(study)
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
