#!/usr/bin/env python3
"""Recompute the GUILD score and SOLE-R1 falsification result."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def guild_score(data: dict[str, object]) -> dict[str, object]:
    selected = data["selected_method"]
    baselines = ["vlm_uniform_semantic_only", "expert_1", "expert_2"]
    tasks = data["tasks"]
    top = 0
    pairwise = 0
    regrets = []
    methods = [selected, *baselines]
    means = {method: statistics.mean(row[method] for row in tasks) for method in methods}
    for row in tasks:
        values = {method: row[method] for method in methods}
        best = max(values.values())
        top += values[selected] == best
        regrets.append(best - values[selected])
        pairwise += sum(values[selected] >= values[baseline] for baseline in baselines)
    return {
        "top_choice_correct": top,
        "top_choice_total": len(tasks),
        "pairwise_correct": pairwise,
        "pairwise_total": len(tasks) * len(baselines),
        "mean_allocation_regret_pp": statistics.mean(regrets),
        "advantage_over_semantic_only_pp": means[selected] - means["vlm_uniform_semantic_only"],
        "advantage_over_expert_1_pp": means[selected] - means["expert_1"],
        "advantage_over_expert_2_pp": means[selected] - means["expert_2"],
    }


def sole_score(data: dict[str, object]) -> dict[str, object]:
    predicted = data["frozen_exact_overlap_selection"]
    observed = data["downstream_observed_top_choice"]
    return {
        "predicted": predicted,
        "observed": observed,
        "top_choice_correct": predicted == observed,
        "false_completion_control_correct": data["lower_false_completion_selection"] == observed,
        "outcomes_read_for_selection": data["chronology"]["outcomes_read_for_selection"],
    }


if __name__ == "__main__":
    guild = json.loads((ROOT / "data" / "guild.json").read_text())
    sole = json.loads((ROOT / "data" / "sole-r1.json").read_text())
    observed = {"guild": guild_score(guild), "sole_r1": sole_score(sole)}
    expected = json.loads((ROOT / "results" / "summary.json").read_text())
    if observed != expected:
        raise SystemExit("recomputed robotics summary does not match the released result")
    print(json.dumps(observed, indent=2, sort_keys=True))
