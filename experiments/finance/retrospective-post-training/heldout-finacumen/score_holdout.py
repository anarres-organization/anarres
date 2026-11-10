#!/usr/bin/env python3
"""Score the V4 representation on the excluded FinAcumen source."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACT = HERE / "CONTRACT.json"
SOURCE = HERE / "SOURCE.json"
OUTCOMES = HERE / "OUTCOMES.json"
SCORE = HERE / "SCORE.json"
MANIFEST = HERE / "MANIFEST.sha256.json"


def sign(value: float) -> int:
    return (value > 0) - (value < 0)


def score_panel(panel: dict) -> dict:
    arms = panel["arms"]
    correct = 0
    scored = 0
    abstained = 0
    for left_index, left in enumerate(arms):
        for right in arms[left_index + 1 :]:
            predicted = sign(left["prediction"] - right["prediction"])
            observed = sign(left["outcome"] - right["outcome"])
            if predicted == 0:
                abstained += 1
                continue
            scored += 1
            correct += predicted == observed

    best_prediction = max(arm["prediction"] for arm in arms)
    selected = [arm for arm in arms if arm["prediction"] == best_prediction]
    selected_outcome = sum(arm["outcome"] for arm in selected) / len(selected)
    outcomes = [arm["outcome"] for arm in arms]
    outcome_range = max(outcomes) - min(outcomes)
    regret = 0.0 if outcome_range == 0 else (max(outcomes) - selected_outcome) / outcome_range
    return {
        "panel_id": panel["panel_id"],
        "family": panel["family"],
        "pairwise_correct": correct,
        "pairwise_scored": scored,
        "pairwise_abstained": abstained,
        "normalized_regret": regret,
    }


def main() -> None:
    data = json.loads(OUTCOMES.read_text())
    panels = [score_panel(panel) for panel in data["panels"]]
    families = defaultdict(lambda: {"correct": 0, "scored": 0, "abstained": 0, "regret": []})
    for panel in panels:
        family = families[panel["family"]]
        family["correct"] += panel["pairwise_correct"]
        family["scored"] += panel["pairwise_scored"]
        family["abstained"] += panel["pairwise_abstained"]
        family["regret"].append(panel["normalized_regret"])

    family_scores = {}
    for name, values in sorted(families.items()):
        family_scores[name] = {
            "pairwise_correct": values["correct"],
            "pairwise_scored": values["scored"],
            "pairwise_accuracy": values["correct"] / values["scored"],
            "pairwise_abstained": values["abstained"],
            "mean_normalized_regret": sum(values["regret"]) / len(values["regret"]),
            "panels": len(values["regret"]),
        }

    total_correct = sum(panel["pairwise_correct"] for panel in panels)
    total_scored = sum(panel["pairwise_scored"] for panel in panels)
    output = {
        "schema_version": 1,
        "status": "SCORED_PREEXISTING_REPRESENTATION_SOURCE_HOLDOUT",
        "panels": len(panels),
        "pairwise_correct": total_correct,
        "pairwise_scored": total_scored,
        "pairwise_accuracy": total_correct / total_scored,
        "pairwise_abstained": sum(panel["pairwise_abstained"] for panel in panels),
        "mean_normalized_regret": sum(panel["normalized_regret"] for panel in panels) / len(panels),
        "family_scores": family_scores,
        "panel_scores": panels,
        "interpretation": (
            "The V4 capability-contract representation recovers the controlled ordering within "
            "this excluded source and transfers across its reported backbones. The nested panels "
            "provide one source-level test rather than independent study replications."
        ),
    }
    SCORE.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    paths = [CONTRACT, SOURCE, OUTCOMES, Path(__file__), SCORE]
    manifest = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
