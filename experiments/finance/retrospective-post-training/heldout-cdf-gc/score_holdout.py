#!/usr/bin/env python3
"""Score the pre-existing finance representation on CDF-GC."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def main() -> None:
    predictions = read("PREDICTIONS.json")
    outcomes = read("OUTCOMES.json")["panels"]
    comparisons = []
    best_candidates = []
    regrets = []

    for model, candidate_set in predictions["candidate_sets"].items():
        for target, preferred_key in (
            ("finance", "finance_preferred"),
            ("general", "general_preferred"),
        ):
            preferred = predictions[preferred_key]
            values = outcomes[model][target]
            assert set(candidate_set) == set(values)
            for comparison in candidate_set:
                if comparison == preferred:
                    continue
                margin = values[preferred] - values[comparison]
                comparisons.append(
                    {
                        "model": model,
                        "target": target,
                        "preferred": preferred,
                        "comparison": comparison,
                        "observed_margin": round(margin, 6),
                        "correct": margin > 0,
                    }
                )

            observed = max(values, key=values.get)
            best_candidates.append(
                {
                    "model": model,
                    "target": target,
                    "predicted": preferred,
                    "observed": observed,
                    "correct": preferred == observed,
                }
            )
            spread = max(values.values()) - min(values.values())
            regrets.append((max(values.values()) - values[preferred]) / spread if spread else 0.0)

    correct = sum(item["correct"] for item in comparisons)
    output = {
        "schema_version": 1,
        "status": "SCORED_PREEXISTING_REPRESENTATION_SOURCE_HOLDOUT",
        "directional_correct": correct,
        "directional_scored": len(comparisons),
        "directional_accuracy": round(correct / len(comparisons), 6),
        "best_candidate_correct": sum(item["correct"] for item in best_candidates),
        "best_candidate_scored": len(best_candidates),
        "mean_normalized_regret": round(sum(regrets) / len(regrets), 6),
        "comparisons": comparisons,
        "best_candidates": best_candidates,
        "abstentions": predictions["abstentions"],
        "interpretation": (
            "The pre-existing capability-contract representation recovers 21 of 22 "
            "candidate-target directions across two backbones. It selects CDF-GC for both "
            "finance panels and the starting model for one of two general-retention panels. "
            "The result is one retrospective excluded-source test."
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
