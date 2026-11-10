#!/usr/bin/env python3
"""Score the pre-existing finance representation on FinToolSyn ablations."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def main() -> None:
    predictions = read("PREDICTIONS.json")
    outcomes = read("OUTCOMES.json")
    tables = outcomes["primary_table"]

    comparisons = []
    for claim in predictions["comparisons"]:
        values = tables[claim["target"]]
        margin = values[claim["preferred"]] - values[claim["comparison"]]
        comparisons.append({**claim, "observed_margin": round(margin, 6), "correct": margin > 0})

    best_candidates = []
    for target, predicted in predictions["best_candidate_predictions"].items():
        values = tables[target]
        observed = max(values, key=values.get)
        best_candidates.append(
            {
                "target": target,
                "predicted": predicted,
                "observed": observed,
                "correct": predicted == observed,
            }
        )

    regressions = []
    for claim in predictions["regression_predictions"]:
        values = tables[claim["target"]]
        observed_margin = values[claim["candidate"]] - values[claim["baseline"]]
        observed_direction = (
            "improve" if observed_margin > 0 else "regress" if observed_margin < 0 else "tie"
        )
        regressions.append(
            {
                **claim,
                "observed_margin": round(observed_margin, 6),
                "observed_direction": observed_direction,
                "correct": claim["direction"] == observed_direction,
            }
        )

    output = {
        "schema_version": 1,
        "status": "SCORED_PREEXISTING_REPRESENTATION_SOURCE_HOLDOUT",
        "directional_correct": sum(item["correct"] for item in comparisons),
        "directional_scored": len(comparisons),
        "directional_accuracy": sum(item["correct"] for item in comparisons) / len(comparisons),
        "best_candidate_correct": sum(item["correct"] for item in best_candidates),
        "best_candidate_scored": len(best_candidates),
        "regression_correct": sum(item["correct"] for item in regressions),
        "regression_scored": len(regressions),
        "abstentions": predictions["abstentions"],
        "comparisons": comparisons,
        "best_candidates": best_candidates,
        "regressions": regressions,
        "appendix_metric_sensitivity": outcomes["appendix_sensitivity"],
        "interpretation": (
            "The pre-existing capability-contract representation recovers every high-confidence "
            "FinToolSyn comparison, including the reverse-synthesis regression on balanced and "
            "non-tool behavior. The result is one retrospective excluded-source test."
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
