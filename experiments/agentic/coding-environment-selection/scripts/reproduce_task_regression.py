#!/usr/bin/env python3
"""Reconstruct the compact task-level coding regression summary."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "task-regression-risk.json"
EXPECTED = ROOT / "results" / "task-regression-summary.json"


def canonical(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def compute() -> dict[str, object]:
    record = json.loads(DATA.read_text())
    support = record["support"]
    metrics = record["metrics"]
    bootstrap = record["repository_clustered_bootstrap"]
    return {
        "artifact": "agentic_coding_task_regression_summary_v1",
        "combined_average_precision": metrics["combined"]["average_precision"],
        "combined_auc": metrics["combined"]["roc_auc"],
        "combined_auc_gain_over_starting_behavior": bootstrap[
            "combined_minus_starting_behavior_auc"
        ],
        "combined_auc_gain_repository_clustered_ci95": bootstrap["ci95"],
        "held_out_repositories": support["held_out_repositories"],
        "held_out_tasks": support["held_out_tasks"],
        "severe_regressions": support["severe_regressions"],
        "starting_behavior_auc": metrics["starting_behavior"]["roc_auc"],
        "task_environment_outcomes": support["task_environment_outcomes"],
        "top_20pct_precision": metrics["combined"]["top_20pct_precision"],
        "top_20pct_recall": metrics["combined"]["top_20pct_recall"],
    }


def main() -> None:
    actual = compute()
    if actual != json.loads(EXPECTED.read_text()):
        raise SystemExit("recomputed task-regression audit does not match released summary")
    print(canonical(actual), end="")


if __name__ == "__main__":
    main()
