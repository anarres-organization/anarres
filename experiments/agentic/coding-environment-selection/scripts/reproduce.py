#!/usr/bin/env python3
"""Recompute public agentic-coding selection results from compact inputs."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANELS = ROOT / "data" / "panels.json"
EXPECTED = ROOT / "results" / "summary.json"


def canonical(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def select(candidates: list[dict[str, float | str]], rule: str) -> str:
    if rule == "policy_response_rule":
        eligible = [row for row in candidates if 0.10 <= float(row["readiness"]) <= 0.85]
        return str(max(eligible, key=lambda row: float(row["reward_information"]) / float(row["cost"]))["id"])
    coordinate, direction = {
        "readiness": ("readiness", 1),
        "reward_information": ("reward_information", 1),
        "target_affinity": ("target_affinity", 1),
        "lowest_cost": ("cost", -1),
    }[rule]
    return str(max(candidates, key=lambda row: direction * float(row[coordinate]))["id"])


def compute(data: dict[str, object]) -> dict[str, object]:
    rules = ["policy_response_rule", "readiness", "reward_information", "target_affinity", "lowest_cost"]
    decisions: list[dict[str, object]] = []
    regrets = {rule: [] for rule in rules}
    wins = {rule: 0 for rule in rules}
    for panel in data["panels"]:
        candidates = panel["candidates"]
        choices = {rule: select(candidates, rule) for rule in rules}
        for endpoint, outcome in panel["outcomes"].items():
            best = max(outcome, key=outcome.get)
            best_value = outcome[best]
            row = {
                "panel": panel["panel_id"],
                "endpoint": endpoint,
                "observed_best": best,
                "choices": choices,
                "regret_pp": {},
            }
            for rule, choice in choices.items():
                regret = 100 * (best_value - outcome[choice])
                regrets[rule].append(regret)
                wins[rule] += int(choice == best)
                row["regret_pp"][rule] = round(regret, 6)
            decisions.append(row)
    aggregates = {
        rule: {
            "best_endpoint_decisions": wins[rule],
            "mean_regret_pp": round(sum(values) / len(values), 6),
        }
        for rule, values in regrets.items()
    }
    return {
        "artifact": "agentic_coding_environment_selection_summary_v1",
        "independent_training_decisions": len(data["panels"]),
        "nested_reported_endpoints": len(decisions),
        "decisions": decisions,
        "aggregate": aggregates,
        "interpretation": {
            "primary_result": "The frozen policy-response rule selects the best candidate on three of four nested endpoints with 0.10 percentage-point mean regret.",
            "baseline_result": "Readiness alone has 2.355 percentage-point mean regret.",
            "boundary": "Reward information alone makes the same choices, so these panels do not establish incremental decision value for the readiness gate or cost normalization.",
        },
    }


def main() -> None:
    actual = compute(json.loads(PANELS.read_text()))
    serialized = canonical(actual)
    if actual != json.loads(EXPECTED.read_text()):
        raise SystemExit("recomputed summary does not match results/summary.json")
    print(serialized, end="")


if __name__ == "__main__":
    main()
