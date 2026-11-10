#!/usr/bin/env python3
"""Recompute the GUILD score and SOLE-R1 falsification result."""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ROOT / "results" / "summary.json"


def canonical_json(value: dict[str, object]) -> str:
    """Serialize one released artifact in its byte-stable form."""
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


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


def average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and values[order[end + 1]] == values[order[start]]:
            end += 1
        rank = (start + end) / 2
        for index in order[start : end + 1]:
            ranks[index] = rank
        start = end + 1
    return ranks


def correlation(x: list[float], y: list[float]) -> float:
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)
    numerator = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y, strict=True))
    x_norm = math.sqrt(sum((a - x_mean) ** 2 for a in x))
    y_norm = math.sqrt(sum((b - y_mean) ** 2 for b in y))
    return numerator / (x_norm * y_norm)


def greenball_score(data: dict[str, object]) -> dict[str, object]:
    cells = data["cells"]
    budgets = sorted({row["budget"] for row in cells})
    selected = 0
    for budget in budgets:
        untrimmed = next(
            row for row in cells if row["budget"] == budget and row["recipe"] == "untrimmed"
        )
        trimmed = next(
            row for row in cells if row["budget"] == budget and row["recipe"] == "trimmed"
        )
        selected += trimmed["offline_start_rate"] > untrimmed["offline_start_rate"]
    return {
        "matched_budget_wins": selected,
        "matched_budget_total": len(budgets),
        "spearman_offline_vs_physical_start": correlation(
            average_ranks([row["offline_start_rate"] for row in cells]),
            average_ranks([row["physical_start_rate"] for row in cells]),
        ),
        "demonstration_count_can_choose_recipe": False,
        "outcomes_read_during_measurement": data["chronology"]["outcomes_read_during_measurement"],
    }


if __name__ == "__main__":
    guild = json.loads((ROOT / "data" / "guild.json").read_text())
    sole = json.loads((ROOT / "data" / "sole-r1.json").read_text())
    greenball = json.loads((ROOT / "data" / "greenball-initiation.json").read_text())
    observed = {
        "greenball_initiation": greenball_score(greenball),
        "guild": guild_score(guild),
        "sole_r1": sole_score(sole),
    }
    serialized = canonical_json(observed)
    if serialized != EXPECTED.read_text():
        raise SystemExit("recomputed robotics summary does not byte-match the released result")
    print(serialized, end="")
