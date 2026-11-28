#!/usr/bin/env python3
"""Score frozen domain record-conditioned predictions after receipt creation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "base_record_conditioned_scorer", HERE / "score_record_conditioned_model.py"
)
assert SPEC and SPEC.loader
BASE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE
SPEC.loader.exec_module(BASE)

PREDICTIONS = HERE / "DOMAIN_RECORD_CONDITIONED_PREDICTIONS.jsonl"
RECEIPT = HERE / "DOMAIN_RECORD_CONDITIONED_PREDICTION_RECEIPT.json"
LABELS = HERE / "DOMAIN_RECORD_CONDITIONED_LABELS.jsonl"
RESULTS = HERE / "DOMAIN_RECORD_CONDITIONED_RESULTS.json"
BASELINES = HERE / "DOMAIN_MATCHED_TEXT_BASELINE_RESULTS.json"
RECORDS = HERE / "DOMAIN_SURROGATE_RECORDS.jsonl"

BASE.LABELS = LABELS
BASE.BASELINES = BASELINES


def study_domain_map() -> dict[str, str]:
    domains: dict[str, set[str]] = defaultdict(set)
    for row in map(json.loads, RECORDS.read_text().splitlines()):
        domains[row["study_id"]].add(row["domain"])
    if any(len(values) != 1 for values in domains.values()):
        raise ValueError("every held-out study must map to exactly one domain")
    return {study: next(iter(values)) for study, values in domains.items()}


def summarize_domains(
    study_results: dict[str, dict], study_domains: dict[str, str]
) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for study, result in study_results.items():
        grouped[study_domains[study]].append(result)
    metrics = ("normalized_regret", "pairwise_ordering", "top_choice_credit", "confidence")
    return {
        domain: {
            "studies": len(rows),
            "panels": sum(row["panels"] for row in rows),
            **{
                f"study_macro_{metric}": sum(row[metric] for row in rows) / len(rows)
                for metric in metrics
            },
            "study_macro_abstention": sum(row["abstention"] for row in rows) / len(rows),
        }
        for domain, rows in sorted(grouped.items())
    }


def paired_comparison_by_domain(
    summaries: dict[str, dict],
    baseline: str,
    candidate: str,
    study_domains: dict[str, str],
) -> dict[str, dict]:
    domains = sorted(set(study_domains.values()))
    return {
        domain: BASE.paired_comparison(
            {
                condition: {
                    "study_results": {
                        study: result
                        for study, result in summaries[condition]["study_results"].items()
                        if study_domains[study] == domain
                    }
                }
                for condition in (baseline, candidate)
            },
            baseline,
            candidate,
        )
        for domain in domains
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, default=PREDICTIONS)
    parser.add_argument("--receipt", type=Path, default=RECEIPT)
    parser.add_argument("--output", type=Path, default=RESULTS)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text())
    if receipt["predictions_sha256"] != BASE.sha256(args.predictions):
        raise ValueError("prediction receipt digest mismatch")
    predictions = {
        row["prompt_id"]: row for row in map(json.loads, args.predictions.read_text().splitlines())
    }
    labels = {row["prompt_id"]: row for row in map(json.loads, LABELS.read_text().splitlines())}
    if predictions.keys() != labels.keys():
        raise ValueError("predictions do not cover the frozen target set")
    scored: dict[str, list[dict]] = defaultdict(list)
    for prompt_id, row in predictions.items():
        metrics = BASE.panel_metrics(row["prediction"], labels[prompt_id])
        scored[row["condition"]].append({**row, **metrics})
    summaries = {condition: BASE.summarize(rows) for condition, rows in sorted(scored.items())}
    study_domains = study_domain_map()
    for summary in summaries.values():
        summary["domain_results"] = summarize_domains(summary["study_results"], study_domains)
    result = {
        "artifact": "anarres_domain_record_conditioned_results_v1",
        "evidence_tier": "retrospective balanced complete-group development replay",
        "inputs": {
            "predictions_sha256": BASE.sha256(args.predictions),
            "prediction_receipt_sha256": BASE.sha256(args.receipt),
            "protected_labels_sha256": BASE.sha256(LABELS),
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
        "matched_text_baselines": BASE.matched_baseline_summary(summaries),
        "paired_comparisons": {
            "primary_retrieval_contrast": BASE.paired_comparison(
                summaries,
                "zero_history_with_measurements",
                "retrieved_history_with_measurements",
            ),
            "zero_history_measurement_contrast": BASE.paired_comparison(
                summaries,
                "zero_history_without_measurements",
                "zero_history_with_measurements",
            ),
            "retrieved_history_measurement_contrast": BASE.paired_comparison(
                summaries,
                "retrieved_history_without_measurements",
                "retrieved_history_with_measurements",
            ),
            "retrieval_contrast_without_measurements": BASE.paired_comparison(
                summaries,
                "zero_history_without_measurements",
                "retrieved_history_without_measurements",
            ),
        },
        "primary_retrieval_contrast_by_domain": paired_comparison_by_domain(
            summaries,
            "zero_history_with_measurements",
            "retrieved_history_with_measurements",
            study_domains,
        ),
        "cost_accounting": {
            "inference": "All attempts, tokens, and request time are charged.",
            "measurement": "Missing common measurement costs remain unknown.",
            "candidate_training": "No new candidate training occurs in this replay.",
        },
        "claim_boundary": (
            "Retrospective development replay on an outcome-blind balanced panel sample. "
            "Confidence is not calibrated uncertainty, and the result cannot authorize "
            "prospective allocation by itself."
        ),
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
