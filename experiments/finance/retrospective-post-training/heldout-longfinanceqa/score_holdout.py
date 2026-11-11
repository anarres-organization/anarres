#!/usr/bin/env python3
"""Score the frozen LongFinanceQA component predictions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def verify_freeze() -> None:
    for line in (HERE / "FREEZE_MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
        expected, name = line.split("  ", 1)
        observed = hashlib.sha256((HERE / name).read_bytes()).hexdigest()
        if observed != expected:
            raise RuntimeError(f"frozen artifact changed: {name}")


def comparison(
    prediction_id: str,
    subset: str,
    metric: str,
    preferred: float,
    comparison_value: float,
) -> dict:
    margin = round(preferred - comparison_value, 6)
    return {
        "prediction_id": prediction_id,
        "subset": subset,
        "metric": metric,
        "observed_margin": margin,
        "correct": margin > 0,
    }


def main() -> None:
    verify_freeze()
    outcomes = read("OUTCOMES.json")
    rows = outcomes["supervised_cot_ablation"]
    comparisons = []

    for subset, values in rows.items():
        comparisons.append(
            comparison(
                "cot_vs_answer_only_finance",
                subset,
                "overall",
                values["cot"]["overall"],
                values["answer_only"]["overall"],
            )
        )
        for metric in ("comparison", "clustering", "chain_reasoning"):
            comparisons.append(
                comparison(
                    "cot_vs_answer_only_multisource",
                    subset,
                    metric,
                    values["cot"][metric],
                    values["answer_only"][metric],
                )
            )
        comparisons.append(
            comparison(
                "simple_context_retention",
                subset,
                "single_source",
                values["cot"]["single_source"],
                values["answer_only"]["single_source"],
            )
        )

    for subset, values in outcomes["property_extraction_ablation"].items():
        comparisons.append(
            comparison(
                "property_extraction_component",
                subset,
                "overall",
                values["full_pai"],
                values["without_property_extraction"],
            )
        )

    prediction_ids = [
        "cot_vs_answer_only_finance",
        "cot_vs_answer_only_multisource",
        "property_extraction_component",
        "simple_context_retention",
    ]
    family_scores = []
    for prediction_id in prediction_ids:
        covered = [item for item in comparisons if item["prediction_id"] == prediction_id]
        family_scores.append(
            {
                "prediction_id": prediction_id,
                "correct": sum(item["correct"] for item in covered),
                "scored": len(covered),
                "supported": sum(item["correct"] for item in covered) > len(covered) / 2,
            }
        )

    correct = sum(item["correct"] for item in comparisons)
    output = {
        "schema_version": 1,
        "status": "SCORED_OUTCOME_SEPARATED_COMPONENT_TEST",
        "source_level_tests": 1,
        "directional_correct": correct,
        "directional_scored": len(comparisons),
        "directional_accuracy": correct / len(comparisons),
        "prediction_families_supported": sum(item["supported"] for item in family_scores),
        "prediction_families_scored": len(family_scores),
        "family_scores": family_scores,
        "comparisons": comparisons,
        "unscored_predictions": [
            {
                "prediction_id": "property_retrieval_component",
                "reason": (
                    "The paper does not report a matched PAI ablation that removes only "
                    "property-based retrieval."
                ),
            },
            {
                "prediction_id": "intermediate_summarization_component",
                "reason": (
                    "The paper does not report a matched PAI ablation that removes only "
                    "intermediate summarization."
                ),
            },
        ],
        "interpretation": (
            "The outcome-separated test supports all four scoreable prediction families. "
            "Across 25 reported matched comparisons, 24 have the frozen direction; the one miss "
            "is clustering at 10K-50K tokens. This remains one source-level test, not 25 "
            "independent studies."
        ),
    }
    (HERE / "SCORE.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    files = [
        "CONTRACT.json",
        "FREEZE_MANIFEST.sha256",
        "OUTCOMES.json",
        "PREDICTIONS.json",
        "README.md",
        "RESULT.md",
        "SCORE.json",
        "SOURCE.json",
        "score_holdout.py",
        "test_score.py",
    ]
    manifest = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in files}
    (HERE / "MANIFEST.sha256.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
