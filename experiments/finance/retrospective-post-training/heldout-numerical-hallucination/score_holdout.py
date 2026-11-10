#!/usr/bin/env python3
"""Score the frozen numerical-faithfulness source holdout."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FREEZE = HERE / "FREEZE.json"
SOURCE = HERE / "SOURCE.json"
OUTCOMES = HERE / "OUTCOMES.json"
SCORE = HERE / "SCORE.json"
MANIFEST = HERE / "MANIFEST.sha256.json"


def main() -> None:
    freeze = json.loads(FREEZE.read_text())
    outcomes = json.loads(OUTCOMES.read_text())
    primary = outcomes["primary_volume_matched"]
    primary_correct = primary["observed_winner"] == "finance_qa_and_numeracy_3500"
    full = outcomes["full_recipe"]["observed_winner_by_level"]
    full_correct = {
        level: winner == "finance_qa_and_numeracy_3500" for level, winner in full.items()
    }
    directional = [primary_correct, *full_correct.values()]
    output = {
        "schema_version": 1,
        "status": "SCORED_AFTER_FREEZE",
        "freeze_commit": "50c6583",
        "primary_prediction_correct": primary_correct,
        "full_recipe_prediction_correct_by_level": full_correct,
        "directional_accuracy": sum(directional) / len(directional),
        "directional_comparisons": len(directional),
        "abstentions": {
            "count": 1,
            "base_vs_finance_language": {
                "decision": "abstain",
                "observed_winner": outcomes["base_vs_finance_language"]["observed_winner"],
                "interpretation": (
                    "the representation avoided a false preference but did not select "
                    "the clearly safer base model"
                ),
            },
        },
        "diagnosis": {
            "missing_coordinate": "behavioral contract and grounding-discipline alignment",
            "evidence": (
                "numeracy data improved constrained calculation but reinforced "
                "unsupported numerical generation during summarization"
            ),
            "representation_change": (
                "separate task-content alignment from alignment with grounded "
                "generation, abstention, and output constraints"
            ),
        },
        "frozen_prediction_count": len(freeze["predictions"]),
    }
    SCORE.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    paths = [FREEZE, SOURCE, OUTCOMES, Path(__file__), SCORE]
    manifest = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
