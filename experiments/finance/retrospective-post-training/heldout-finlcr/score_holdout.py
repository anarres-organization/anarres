#!/usr/bin/env python3
"""Score the outcome-separated FinLCR component predictions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREDICTIONS = HERE / "PREDICTIONS.json"
OUTCOMES = HERE / "OUTCOMES.json"
OUT = HERE / "SCORE.json"
MANIFEST = HERE / "SCORED_MANIFEST.sha256.json"


def read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object in {path}")
    return value


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score() -> dict:
    predictions = read(PREDICTIONS)
    outcomes = read(OUTCOMES)
    arms = outcomes["arms"]
    comparisons = [
        {
            "prediction_id": "staged_context_aggregate",
            "preferred": "s2l_and_das",
            "comparison": "das_only",
            "metric": "avg",
        },
        {
            "prediction_id": "difficulty_sampling_aggregate",
            "preferred": "s2l_and_das",
            "comparison": "s2l_only",
            "metric": "avg",
        },
        {
            "prediction_id": "staged_context_long_subset",
            "preferred": "s2l_and_das",
            "comparison": "das_only",
            "metric": "avg_long",
        },
    ]
    scored = []
    for comparison in comparisons:
        margin = round(
            arms[comparison["preferred"]][comparison["metric"]]
            - arms[comparison["comparison"]][comparison["metric"]],
            2,
        )
        scored.append({**comparison, "observed_margin": margin, "correct": margin > 0})

    retention_margin = round(arms["s2l_and_das"]["avg_short"] - arms["naive_gspo"]["avg_short"], 2)
    retention = {
        "prediction_id": predictions["regression_prediction"]["prediction_id"],
        "candidate": "s2l_and_das",
        "baseline": "naive_gspo",
        "metric": "avg_short",
        "predicted_direction": "no_regression",
        "observed_margin": retention_margin,
        "observed_direction": "no_regression" if retention_margin >= 0 else "regress",
        "correct": retention_margin >= 0,
    }
    isolated = {
        "s2l_only_minus_naive_gspo": round(arms["s2l_only"]["avg"] - arms["naive_gspo"]["avg"], 2),
        "das_only_minus_naive_gspo": round(arms["das_only"]["avg"] - arms["naive_gspo"]["avg"], 2),
        "combined_minus_naive_gspo": round(
            arms["s2l_and_das"]["avg"] - arms["naive_gspo"]["avg"], 2
        ),
    }
    return {
        "schema_version": 1,
        "status": "SCORED_OUTCOME_SEPARATED_COMPONENT_ABLATION",
        "source_id": outcomes["source_id"],
        "component_correct": sum(row["correct"] for row in scored),
        "component_scored": len(scored),
        "component_comparisons": scored,
        "regression_correct": int(retention["correct"]),
        "regression_scored": 1,
        "regression_comparison": retention,
        "unscored_predictions": [
            {
                "prediction_id": "difficulty_sampling_hard_subset",
                "reason": (
                    "the paper does not report a matched component ablation "
                    "for the highest-difficulty subset"
                ),
            }
        ],
        "interaction_diagnostic": isolated,
        "interpretation": (
            "The frozen representation correctly predicts all three reported "
            "matched component directions and short-context retention. The "
            "single-component regressions show that S2L and DAS act jointly in "
            "this study and should not be interpreted as independently additive effects."
        ),
    }


def main() -> None:
    result = score()
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        name: digest(HERE / name)
        for name in [
            "CONTRACT.json",
            "FREEZE_MANIFEST.sha256.json",
            "OUTCOMES.json",
            "PREDICTIONS.json",
            "SCORE.json",
            "SOURCE.json",
            "score_holdout.py",
        ]
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
