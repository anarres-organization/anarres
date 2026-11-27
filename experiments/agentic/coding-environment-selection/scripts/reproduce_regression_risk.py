#!/usr/bin/env python3
"""Recompute the source-contained coding regression-risk audit."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "regression-risk.json"
EXPECTED = ROOT / "results" / "regression-risk-summary.json"


def canonical(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def average_precision(labels: list[bool], scores: list[float]) -> float:
    positives = sum(labels)
    if positives == 0:
        return 0.0
    ordered = sorted(zip(scores, labels, strict=True), reverse=True)
    total = 0.0
    seen_positive = 0
    index = 0
    while index < len(ordered):
        score = ordered[index][0]
        group = []
        while index < len(ordered) and ordered[index][0] == score:
            group.append(ordered[index][1])
            index += 1
        group_positive = sum(group)
        if group_positive:
            total += group_positive * (seen_positive + group_positive) / index
        seen_positive += group_positive
    return total / positives


def roc_auc(labels: list[bool], scores: list[float]) -> float:
    positive_scores = [score for label, score in zip(labels, scores, strict=True) if label]
    negative_scores = [score for label, score in zip(labels, scores, strict=True) if not label]
    credit = 0.0
    for positive in positive_scores:
        for negative in negative_scores:
            credit += float(positive > negative) + 0.5 * float(positive == negative)
    return credit / (len(positive_scores) * len(negative_scores))


def metrics(labels: list[bool], scores: list[float]) -> dict[str, float]:
    return {
        "roc_auc": round(roc_auc(labels, scores), 6),
        "average_precision": round(average_precision(labels, scores), 6),
        "brier": round(
            sum((float(label) - score) ** 2 for label, score in zip(labels, scores, strict=True))
            / len(labels),
            6,
        ),
    }


def compute() -> dict[str, object]:
    data = json.loads(DATA.read_text())
    labels = []
    audit_shift_scores = []
    shift_scores = []
    starting_scores = []
    rows = []
    for run in data["runs"]:
        training = data["training_sets"][run["training_set"]]
        for target_id, delta_key in (
            ("verified397", "verified397_delta"),
            ("swe_bench_pro", "swe_bench_pro_delta"),
        ):
            target = data["targets"][target_id]
            label = float(run[delta_key]) < 0
            audited = bool(training["execution_audited"])
            shifted = bool(target["shifted_target"])
            audit_score = 0.0 if audited else 0.5 + 0.5 * float(shifted)
            labels.append(label)
            audit_shift_scores.append(audit_score)
            shift_scores.append(float(shifted))
            starting_scores.append(float(training["base_pass_rate"]))
            rows.append(
                {
                    "training_set": run["training_set"],
                    "seed": run["seed"],
                    "target": target_id,
                    "delta_pp": run[delta_key],
                    "regression": label,
                    "risk_score": audit_score,
                }
            )
    high_risk = [row for row in rows if row["risk_score"] == 1.0]
    return {
        "artifact": "agentic_coding_regression_risk_summary_v1",
        "seed_target_outcomes": len(rows),
        "regressions": sum(labels),
        "risk_rule": metrics(labels, audit_shift_scores),
        "target_shift_only": metrics(labels, shift_scores),
        "starting_pass_rate": metrics(labels, starting_scores),
        "high_risk_group": {
            "rows": len(high_risk),
            "regressions_captured": sum(row["regression"] for row in high_risk),
            "recall": round(sum(row["regression"] for row in high_risk) / sum(labels), 6),
            "precision": round(sum(row["regression"] for row in high_risk) / len(high_risk), 6),
        },
        "audited_seed_target_regressions": sum(
            row["regression"] for row in rows if row["training_set"].startswith("clean")
        ),
        "unaudited_pro_regressions": sum(
            row["regression"]
            for row in rows
            if not row["training_set"].startswith("clean") and row["target"] == "swe_bench_pro"
        ),
        "boundary": data["claim_boundary"],
    }


def main() -> None:
    actual = compute()
    if EXPECTED.exists() and actual != json.loads(EXPECTED.read_text()):
        raise SystemExit("recomputed regression audit does not match released summary")
    print(canonical(actual), end="")


if __name__ == "__main__":
    main()
