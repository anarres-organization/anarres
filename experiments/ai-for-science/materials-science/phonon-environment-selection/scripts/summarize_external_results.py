#!/usr/bin/env python3
"""Create a compact public summary from the complete external score artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path

METRICS = (
    "top_k_stable_rate",
    "continuous_pairwise_concordance",
    "roc_auc",
    "brier_score",
    "minimum_frequency_mae_thz",
)


def canonical_digest(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def aggregate(rows: list[dict], keys: tuple[str, ...]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    result = []
    for identity, values in sorted(groups.items()):
        item = {key: value for key, value in zip(keys, identity, strict=False)}
        item["replicates"] = len(values)
        for metric in METRICS:
            item[metric] = statistics.fmean(float(row[metric]) for row in values)
        result.append(item)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scored-results", type=Path, required=True)
    parser.add_argument("--composition-audit", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    scored = json.loads(args.scored_results.read_text(encoding="utf-8"))
    composition = json.loads(args.composition_audit.read_text(encoding="utf-8"))
    if not scored["external_labels_opened"]:
        raise ValueError("Expected a scored external-result artifact")
    dft = [row for row in scored["run_metrics"] if row["panel"] == "dft_pbe"]
    mp20 = [row for row in scored["run_metrics"] if row["panel"] == "mp20"]
    references = scored["reference_metrics"]
    result = {
        "schema_version": "1.0",
        "study": "prospective-phonon-environment-selection",
        "status": "prospective_prediction_scored",
        "prediction_manifest_sha256": scored["prediction_manifest_sha256"],
        "complete_score_sha256": scored["score_sha256"],
        "composition_audit_sha256": composition["composition_audit_sha256"],
        "frozen_prediction": {
            "best_at_each_budget": "signal_coverage",
            "complete_order": ["signal_coverage", "signal", "coverage", "hash_uniform"],
        },
        "decision_summary": scored["decision_summary"],
        "candidate_decisions": scored["candidate_decisions"],
        "dft_pbe_two_seed_means": aggregate(dft, ("budget_structures", "candidate")),
        "mp20_two_seed_macro_means": aggregate(
            aggregate(mp20, ("run_id", "budget_structures", "candidate", "seed")),
            ("budget_structures", "candidate"),
        ),
        "mp20_two_seed_means_by_generator": aggregate(
            mp20, ("source", "budget_structures", "candidate")
        ),
        "reference_metrics": references,
        "candidate_composition": composition["candidates"],
        "source_pool_composition": composition["source_pool"],
        "interpretation": {
            "prospective_result": (
                "The frozen signal-plus-coverage point prediction missed the best candidate at "
                "all three budgets."
            ),
            "primary_panel": (
                "Coverage leads at 256 and 512 structures; hash-uniform leads at 1024."
            ),
            "secondary_panel": (
                "No candidate mean exceeds the starting checkpoint's macro Top-100 stable rate "
                "on MP20."
            ),
            "post_outcome_audit": (
                "Signal-based candidates substantially shift the training-label distribution "
                "toward unstable structures; this is descriptive evidence for a missing "
                "distribution-matching constraint, not a prospective explanation test."
            ),
        },
    }
    result["result_summary_sha256"] = canonical_digest(result)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"result_summary_sha256={result['result_summary_sha256']}")


if __name__ == "__main__":
    main()
