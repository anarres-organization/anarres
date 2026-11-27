#!/usr/bin/env python3
"""Score frozen record-conditioned predictions after their receipt is written."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
PREDICTIONS = HERE / "RECORD_CONDITIONED_PREDICTIONS.jsonl"
RECEIPT = HERE / "RECORD_CONDITIONED_PREDICTION_RECEIPT.json"
LABELS = HERE / "RECORD_CONDITIONED_LABELS.jsonl"
RESULTS = HERE / "RECORD_CONDITIONED_RESULTS.json"
BASELINES = HERE / "MATCHED_TEXT_BASELINE_RESULTS.json"
BOOTSTRAP_SAMPLES = 10_000
BOOTSTRAP_SEED = 20_261_127


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def panel_metrics(prediction: dict[str, Any], label: dict[str, Any]) -> dict[str, float | bool]:
    actual = {
        row["candidate_key"]: float(row["observed_normalized_utility"])
        for row in label["candidates"]
    }
    scores = {key: float(value) for key, value in prediction["candidate_scores"].items()}
    if set(actual) != set(scores):
        raise ValueError("prediction and target candidates differ")
    chosen = [
        key
        for key, value in scores.items()
        if np.isclose(value, max(scores.values()), rtol=0, atol=1e-12)
    ]
    best = max(actual.values())
    pairwise = []
    for left, right in combinations(sorted(actual), 2):
        observed_sign = np.sign(actual[left] - actual[right])
        predicted_sign = np.sign(scores[left] - scores[right])
        pairwise.append(
            0.5
            if observed_sign == 0 or predicted_sign == 0
            else float(observed_sign == predicted_sign)
        )
    return {
        "normalized_regret": best - float(np.mean([actual[key] for key in chosen])),
        "pairwise_ordering": float(np.mean(pairwise)) if pairwise else 0.5,
        "top_choice_credit": float(np.mean([np.isclose(actual[key], best) for key in chosen])),
        "abstain": bool(prediction["abstain"]),
        "confidence": float(prediction["confidence"]),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_study: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_study[row["heldout_study"]].append(row)
    metrics = ("normalized_regret", "pairwise_ordering", "top_choice_credit", "confidence")
    study_results = {
        study: {
            "panels": len(study_rows),
            **{metric: float(np.mean([row[metric] for row in study_rows])) for metric in metrics},
            "abstention": float(np.mean([row["abstain"] for row in study_rows])),
        }
        for study, study_rows in sorted(by_study.items())
    }
    return {
        "studies": len(by_study),
        "panels": len(rows),
        "study_results": study_results,
        "inference": {
            "requests": len(rows),
            "attempts": sum(len(row["usage"]["attempts"]) for row in rows),
            "prompt_tokens": sum(row["usage"]["prompt_tokens"] for row in rows),
            "completion_tokens": sum(row["usage"]["completion_tokens"] for row in rows),
            "total_tokens": sum(row["usage"]["total_tokens"] for row in rows),
            "elapsed_seconds": sum(row["usage"]["elapsed_seconds"] for row in rows),
        },
        **{
            f"study_macro_{metric}": float(
                np.mean(
                    [
                        np.mean([row[metric] for row in study_rows])
                        for study_rows in by_study.values()
                    ]
                )
            )
            for metric in metrics
        },
        "study_macro_abstention": float(
            np.mean(
                [
                    np.mean([row["abstain"] for row in study_rows])
                    for study_rows in by_study.values()
                ]
            )
        ),
    }


def paired_comparison(
    summaries: dict[str, dict[str, Any]], baseline: str, candidate: str
) -> dict[str, Any]:
    studies = sorted(summaries[baseline]["study_results"])
    if studies != sorted(summaries[candidate]["study_results"]):
        raise ValueError("paired conditions cover different held-out studies")
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    result: dict[str, Any] = {
        "baseline": baseline,
        "candidate": candidate,
        "independent_studies": len(studies),
        "bootstrap_samples": BOOTSTRAP_SAMPLES,
        "bootstrap_seed": BOOTSTRAP_SEED,
    }
    for metric in ("normalized_regret", "pairwise_ordering", "top_choice_credit"):
        baseline_values = np.asarray(
            [summaries[baseline]["study_results"][study][metric] for study in studies]
        )
        candidate_values = np.asarray(
            [summaries[candidate]["study_results"][study][metric] for study in studies]
        )
        deltas = (
            baseline_values - candidate_values
            if metric == "normalized_regret"
            else candidate_values - baseline_values
        )
        draws = rng.choice(deltas, size=(BOOTSTRAP_SAMPLES, len(deltas)), replace=True).mean(axis=1)
        result[f"{metric}_improvement"] = {
            "mean": float(np.mean(deltas)),
            "cluster_bootstrap_95_interval": [
                float(np.quantile(draws, 0.025)),
                float(np.quantile(draws, 0.975)),
            ],
            "studies_improved": int(np.sum(deltas > 0)),
            "studies_tied": int(np.sum(np.isclose(deltas, 0.0, rtol=0, atol=1e-12))),
            "studies_worsened": int(np.sum(deltas < 0)),
        }
    return result


def matched_baseline_summary(summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    artifact = json.loads(BASELINES.read_text())
    methods = artifact["methods"]
    best_name = min(
        methods,
        key=lambda name: methods[name]["study_macro_normalized_regret"],
    )
    best = methods[best_name]
    record_condition = min(
        summaries,
        key=lambda name: summaries[name]["study_macro_normalized_regret"],
    )
    baseline_study_results = {
        fold["heldout_study"]: {
            metric: fold[metric]
            for metric in ("normalized_regret", "pairwise_ordering", "top_choice_credit")
        }
        for fold in best["folds"]
    }
    comparison = paired_comparison(
        {
            best_name: {"study_results": baseline_study_results},
            record_condition: summaries[record_condition],
        },
        best_name,
        record_condition,
    )
    return {
        "artifact_sha256": sha256(BASELINES),
        "eligible_methods": sorted(methods),
        "best_method_by_study_macro_regret": best_name,
        "best_method": {
            metric: best[f"study_macro_{metric}"]
            for metric in ("normalized_regret", "pairwise_ordering", "top_choice_credit")
        },
        "best_record_conditioned_condition_by_regret": record_condition,
        "paired_record_conditioned_comparison": comparison,
        "native_rule_note": (
            "Released native rules remain separate because none covers the same nine target "
            "panels under this replay's common scoring contract."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, default=PREDICTIONS)
    parser.add_argument("--receipt", type=Path, default=RECEIPT)
    parser.add_argument("--output", type=Path, default=RESULTS)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text())
    if receipt["predictions_sha256"] != sha256(args.predictions):
        raise ValueError("prediction receipt digest mismatch")
    predictions = {
        row["prompt_id"]: row for row in map(json.loads, args.predictions.read_text().splitlines())
    }
    labels = {row["prompt_id"]: row for row in map(json.loads, LABELS.read_text().splitlines())}
    if predictions.keys() != labels.keys():
        raise ValueError("predictions do not cover the frozen target set")
    scored: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for prompt_id, row in predictions.items():
        metrics = panel_metrics(row["prediction"], labels[prompt_id])
        scored[row["condition"]].append({**row, **metrics})
    summaries = {condition: summarize(rows) for condition, rows in sorted(scored.items())}
    result = {
        "artifact": "anarres_record_conditioned_results_v1",
        "evidence_tier": "retrospective complete-study replay",
        "inputs": {
            "predictions_sha256": sha256(args.predictions),
            "prediction_receipt_sha256": sha256(args.receipt),
            "protected_labels_sha256": sha256(LABELS),
        },
        "conditions": summaries,
        "inference_total": {
            field: sum(summary["inference"][field] for summary in summaries.values())
            for field in (
                "requests",
                "attempts",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "elapsed_seconds",
            )
        },
        "cost_accounting": {
            "inference": "All attempts, tokens, and request time are charged above.",
            "measurement": (
                "The released seed-level records do not contain a common measurement-cost "
                "field, so measurement cost cannot be pooled for this replay."
            ),
            "training": "No new candidate training was run for this retrospective replay.",
            "advancement_consequence": (
                "The total-research-cost advancement rule cannot be evaluated from this "
                "archive alone."
            ),
        },
        "matched_text_baselines": matched_baseline_summary(summaries),
        "paired_comparisons": {
            "primary_measurement_contrast": paired_comparison(
                summaries,
                "cross_history_without_measurements",
                "cross_history_with_measurements",
            ),
            "zero_history_measurement_contrast": paired_comparison(
                summaries,
                "zero_history_without_measurements",
                "zero_history_with_measurements",
            ),
            "history_contrast_without_measurements": paired_comparison(
                summaries,
                "zero_history_without_measurements",
                "cross_history_without_measurements",
            ),
            "history_contrast_with_measurements": paired_comparison(
                summaries,
                "zero_history_with_measurements",
                "cross_history_with_measurements",
            ),
        },
        "claim_boundary": (
            "Retrospective replay on six held-out studies. This does not establish prospective "
            "validity or authorize an adaptive loop."
        ),
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
