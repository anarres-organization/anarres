#!/usr/bin/env python3
"""Score frozen target-conditional claims for the Japanese finance holdout."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    outcomes = json.loads((HERE / "OUTCOMES.json").read_text())
    text_rows = outcomes["text_finance_subtasks"]
    text_wins = sum(
        row["financial_text_adaptation"] > row["unadapted_checkpoint"] for row in text_rows
    )
    path_rows = [row for row in outcomes["full_path_vs_skip_stage"] if row["score_for_direction"]]
    path_wins = sum(row["full_staged_path"] > row["skip_prerequisite_stage"] for row in path_rows)
    output = {
        "schema_version": 1,
        "status": "SCORED_TARGET_CONDITIONAL_SOURCE_HOLDOUT",
        "frozen_comparisons": {
            "text_adaptation_over_base": {
                "status": "SUPPORTED_AT_AGGREGATE_WITH_TASK_REGRESSIONS",
                "correct_targets": text_wins,
                "targets": len(text_rows),
                "aggregate_direction": "correct",
            },
            "visual_adaptation_over_text_only": {
                "status": "UNSCORABLE",
                "reason": outcomes["visual_financial_documents"]["reason"],
            },
            "full_path_over_skip_stage": {
                "status": "NOT_SUPPORTED_AS_A_TARGET_FAMILY_CLAIM",
                "correct_targets": path_wins,
                "targets": len(path_rows),
            },
        },
        "task_level_directional_accuracy": (text_wins + path_wins)
        / (len(text_rows) + len(path_rows)),
        "task_level_correct": text_wins + path_wins,
        "task_level_total": len(text_rows) + len(path_rows),
        "interpretation": (
            "Target conditioning must operate at the task level and include interference and "
            "retention. Broad labels such as text finance or combined financial documents hide "
            "opposing treatment effects."
        ),
    }
    (HERE / "SCORE.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
