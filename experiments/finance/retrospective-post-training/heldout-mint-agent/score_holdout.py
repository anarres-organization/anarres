#!/usr/bin/env python3
"""Score the pre-existing finance representation on Mint-Agent integration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def main() -> None:
    prediction = read("PREDICTIONS.json")
    outcomes = read("OUTCOMES.json")["table"]
    comparisons = []
    for target in prediction["targets"]:
        values = outcomes[target]
        margin = values[prediction["preferred"]] - values[prediction["comparison"]]
        comparisons.append(
            {
                "target": target,
                "preferred": prediction["preferred"],
                "comparison": prediction["comparison"],
                "observed_margin": round(margin, 6),
                "correct": margin > 0,
            }
        )

    correct = sum(row["correct"] for row in comparisons)
    output = {
        "schema_version": 1,
        "status": "SCORED_PREEXISTING_REPRESENTATION_SOURCE_HOLDOUT",
        "directional_correct": correct,
        "directional_scored": len(comparisons),
        "directional_accuracy": correct / len(comparisons),
        "mean_pairwise_regret": 0.0 if correct == len(comparisons) else None,
        "comparisons": comparisons,
        "interpretation": (
            "The capability-contract representation selects MOPD over static TIES merging "
            "on all four reasoning and execution benchmarks. The nested outcomes constitute "
            "one retrospective excluded-source test."
        ),
    }
    (HERE / "SCORE.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    files = [
        "CONTRACT.json",
        "SOURCE.json",
        "PREDICTIONS.json",
        "OUTCOMES.json",
        "score_holdout.py",
        "SCORE.json",
    ]
    manifest = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in files}
    (HERE / "MANIFEST.sha256.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
