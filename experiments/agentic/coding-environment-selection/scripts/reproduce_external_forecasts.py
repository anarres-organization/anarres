#!/usr/bin/env python3
"""Recompute the source-separated AutoEnvScaling external check."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANELS = ROOT / "data" / "external-forecast-panels.json"
EXPECTED = ROOT / "results" / "external-forecast-summary.json"


def canonical(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def choose(candidates: list[dict[str, object]]) -> str | None:
    aligned = [row for row in candidates if row["policy_aligned_progression"] is True]
    if len(aligned) != 1:
        return None
    return str(aligned[0]["id"])


def compute(data: dict[str, object]) -> dict[str, object]:
    decisions = []
    source_regrets: dict[str, dict[str, list[float]]] = {}
    pairwise_correct = 0
    pairwise_total = 0
    for panel in data["panels"]:
        candidates = panel["candidates"]
        scores = {str(row["id"]): float(row["score"]) for row in candidates}
        selected = choose(candidates)
        if selected is None:
            raise ValueError(f"forecast rule abstained on {panel['panel_id']}")
        best = max(scores, key=scores.get)
        best_score = scores[best]
        policy_regret = best_score - scores[selected]
        baseline = "tmax" if panel["source_id"] == "auto_env_scaling" else "environment_ensemble"
        baseline_regret = best_score - scores[baseline]
        source = source_regrets.setdefault(panel["source_id"], {"policy": [], "baseline": []})
        source["policy"].append(policy_regret)
        source["baseline"].append(baseline_regret)
        for candidate_id, score in scores.items():
            if candidate_id == selected:
                continue
            pairwise_total += 1
            pairwise_correct += int(scores[selected] > score)
        decisions.append({
            "panel": panel["panel_id"],
            "source": panel["source_id"],
            "selected": selected,
            "observed_best": best,
            "selected_score": scores[selected],
            "best_score": best_score,
            "policy_feedback_regret_pp": round(policy_regret, 6),
            "baseline": baseline,
            "baseline_regret_pp": round(baseline_regret, 6),
        })
    source_blocks = {}
    for source_id, values in source_regrets.items():
        source_decisions = [row for row in decisions if row["source"] == source_id]
        source_blocks[source_id] = {
            "matched_training_decisions": len(source_decisions),
            "policy_rule_best_decisions": sum(
                row["selected"] == row["observed_best"] for row in source_decisions
            ),
            "policy_rule_mean_regret_pp": round(sum(values["policy"]) / len(values["policy"]), 6),
            "source_baseline_mean_regret_pp": round(
                sum(values["baseline"]) / len(values["baseline"]), 6
            ),
        }
    return {
        "artifact": "agentic_coding_external_forecast_summary_v1",
        "chronology": data["chronology"],
        "matched_training_decisions": len(decisions),
        "forecasted_pairwise_comparisons": pairwise_total,
        "decisions": decisions,
        "aggregate": {
            "policy_aligned_progression_rule": {
                "best_candidate_decisions": sum(
                    row["selected"] == row["observed_best"] for row in decisions
                ),
                "pairwise_correct": pairwise_correct,
                "pairwise_total": pairwise_total,
            },
            "source_blocks": source_blocks,
        },
        "interpretation": {
            "result": (
                "The policy-aligned progression rule selects the reported best candidate "
                "in all six "
                "matched decisions and is correct on all ten forecasted pairwise comparisons."
            ),
            "baseline": (
                "Static TMax has 5.45-point mean regret inside AutoEnvScaling, while environment "
                "ensemble has 11.8-point mean regret inside Environment Evolution."
            ),
            "boundary": (
                "This is a retrospective source-separated external check reconstructed after "
                "publication, not a prospectively frozen forecast or a fitted cross-study "
                "score model."
            ),
        },
    }


def main() -> None:
    actual = compute(json.loads(PANELS.read_text()))
    if actual != json.loads(EXPECTED.read_text()):
        raise SystemExit(
            "recomputed external summary does not match results/external-forecast-summary.json"
        )
    print(canonical(actual), end="")


if __name__ == "__main__":
    main()
