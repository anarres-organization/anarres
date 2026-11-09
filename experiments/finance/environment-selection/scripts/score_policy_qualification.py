#!/usr/bin/env python3
"""Score a starting-policy qualification record without opening held-out data."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

REQUIRED_FIELDS = {
    "policy_id",
    "workflow",
    "scenario_id",
    "rollout_seed",
    "infrastructure_valid",
    "tool_protocol_valid",
    "reward",
    "material_control_violation",
    "generated_tokens",
    "tool_calls",
    "truncated",
}


def read_rows(path: Path) -> list[dict]:
    rows = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        missing = REQUIRED_FIELDS - set(row)
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(f"line {line_number} is missing fields: {names}")
        rows.append(row)
    if not rows:
        raise ValueError("qualification record is empty")
    return rows


def score(
    rows: list[dict],
    expected_workflows: int,
    expected_scenarios_per_workflow: int,
    group_size: int,
) -> dict:
    policies = {row["policy_id"] for row in rows}
    if len(policies) != 1:
        raise ValueError("one qualification record must contain exactly one policy")

    expected_episodes = expected_workflows * expected_scenarios_per_workflow * group_size
    identities = {(row["workflow"], row["scenario_id"], row["rollout_seed"]) for row in rows}
    if len(identities) != len(rows):
        raise ValueError("qualification record contains duplicate episode identities")

    valid_rows = [row for row in rows if row["infrastructure_valid"]]
    infrastructure_failures = len(rows) - len(valid_rows)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in valid_rows:
        groups[(row["workflow"], row["scenario_id"])].append(row)

    complete_groups = {
        key: group
        for key, group in groups.items()
        if len(group) == group_size and all(item["tool_protocol_valid"] for item in group)
    }
    mixed_groups = {
        key: group
        for key, group in complete_groups.items()
        if len({float(item["reward"]) for item in group}) > 1
    }
    mixed_workflows = {workflow for workflow, _ in mixed_groups}

    valid_count = len(valid_rows)
    tool_valid_count = sum(bool(row["tool_protocol_valid"]) for row in valid_rows)
    rewards = [float(row["reward"]) for row in valid_rows if row["tool_protocol_valid"]]
    control_violations = sum(bool(row["material_control_violation"]) for row in valid_rows)
    generated_tokens = [int(row["generated_tokens"]) for row in valid_rows]
    tool_calls = [int(row["tool_calls"]) for row in valid_rows]
    truncated = sum(bool(row["truncated"]) for row in valid_rows)

    completeness = len(rows) == expected_episodes
    tool_valid_rate = tool_valid_count / valid_count if valid_count else 0.0
    completion_rate = sum(reward > 0 for reward in rewards) / len(rewards) if rewards else 0.0
    mixed_fraction = len(mixed_groups) / len(complete_groups) if complete_groups else 0.0
    gates = {
        "planned_episode_completeness": completeness,
        "tool_protocol_valid_rate_at_least_0_98": tool_valid_rate >= 0.98,
        "completion_rate_between_0_02_and_0_80": 0.02 <= completion_rate <= 0.80,
        "mixed_group_fraction_at_least_0_10": mixed_fraction >= 0.10,
        "at_least_two_workflows_with_mixed_groups": len(mixed_workflows) >= 2,
    }

    return {
        "status": "qualification_complete" if completeness else "incomplete",
        "policy_id": next(iter(policies)),
        "expected_episodes": expected_episodes,
        "recorded_episodes": len(rows),
        "infrastructure_failures": infrastructure_failures,
        "valid_episodes": valid_count,
        "tool_protocol_valid_rate": round(tool_valid_rate, 6),
        "completion_rate": round(completion_rate, 6),
        "complete_scenario_groups": len(complete_groups),
        "mixed_scenario_groups": len(mixed_groups),
        "mixed_group_fraction": round(mixed_fraction, 6),
        "workflows_with_mixed_groups": sorted(mixed_workflows),
        "material_control_violation_rate": round(
            control_violations / valid_count if valid_count else 0.0, 6
        ),
        "truncation_rate": round(truncated / valid_count if valid_count else 0.0, 6),
        "median_generated_tokens": statistics.median(generated_tokens)
        if generated_tokens
        else None,
        "median_tool_calls": statistics.median(tool_calls) if tool_calls else None,
        "gates": gates,
        "qualified": completeness and all(gates.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--expected-workflows", type=int, required=True)
    parser.add_argument("--expected-scenarios-per-workflow", type=int, required=True)
    parser.add_argument("--group-size", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    summary = score(
        read_rows(args.input),
        expected_workflows=args.expected_workflows,
        expected_scenarios_per_workflow=args.expected_scenarios_per_workflow,
        group_size=args.group_size,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
