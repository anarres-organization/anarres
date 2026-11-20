#!/usr/bin/env python3
"""Measure repeated starting-agent outcomes on the STATE-Bench train split."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

AUDIT_SPEC = importlib.util.spec_from_file_location(
    "audit_state_bench", Path(__file__).with_name("audit_state_bench.py")
)
AUDIT_MODULE = importlib.util.module_from_spec(AUDIT_SPEC)
assert AUDIT_SPEC.loader is not None
AUDIT_SPEC.loader.exec_module(AUDIT_MODULE)
audit_checkout = AUDIT_MODULE.audit_checkout


def numeric_field(record: dict, direct: str, nested_container: str, nested: str) -> float | None:
    value = record.get(direct)
    if value is None:
        value = record.get(nested_container, {}).get(nested)
    if value is None:
        return None
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{direct} must be numeric when present")
    return float(value)


def read_scored_attempt(path: Path, expected_task_id: str) -> tuple[dict | None, str | None]:
    if not path.exists():
        return None, "missing_file"
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, "malformed_file"
    if record.get("task_id") != expected_task_id:
        raise ValueError(f"{path}: task_id does not match its expected identity")
    if record.get("error"):
        return None, "runtime_error"
    outcome = record.get("task_completion_pass")
    if outcome not in (0, 1, False, True):
        return None, "unscored"
    return {
        "success": int(outcome),
        "output_tokens": numeric_field(record, "output_tokens", "token_usage", "output_tokens"),
        "tool_calls": numeric_field(record, "tool_calls", "efficiency", "tool_calls"),
        "cost_usd": numeric_field(record, "cost_usd", "token_usage", "total_cost_usd"),
    }, None


def loo_absolute_mass(successes: int, attempts: int) -> float:
    if attempts < 2:
        return 0.0
    return 2.0 * successes * (attempts - successes) / (attempts - 1)


def summarize_attempts(
    task_ids: list[str],
    task_types: dict[str, str],
    attempts: dict[str, list[dict]],
    invalid_counts: dict[str, int],
) -> dict:
    per_task = []
    family = defaultdict(lambda: {"tasks": 0, "scored_attempts": 0, "successes": 0})
    total_mass = 0.0
    squared_mass = 0.0
    total_output_tokens = 0.0
    output_tokens_complete = True
    total_tool_calls = 0.0
    tool_calls_complete = True
    total_cost_usd = 0.0
    cost_complete = True

    for task_id in task_ids:
        rows = attempts.get(task_id, [])
        successes = sum(row["success"] for row in rows)
        count = len(rows)
        mass = loo_absolute_mass(successes, count)
        mixed = count >= 2 and 0 < successes < count
        task_type = task_types[task_id]
        family_row = family[task_type]
        family_row["tasks"] += 1
        family_row["scored_attempts"] += count
        family_row["successes"] += successes
        total_mass += mass
        squared_mass += mass * mass

        for row in rows:
            if row["output_tokens"] is None:
                output_tokens_complete = False
            else:
                total_output_tokens += row["output_tokens"]
            if row["tool_calls"] is None:
                tool_calls_complete = False
            else:
                total_tool_calls += row["tool_calls"]
            if row["cost_usd"] is None:
                cost_complete = False
            else:
                total_cost_usd += row["cost_usd"]

        per_task.append(
            {
                "task_id": task_id,
                "task_type": task_type,
                "scored_attempts": count,
                "successes": successes,
                "success_rate": successes / count if count else None,
                "mixed_outcomes": mixed,
                "completion_advantage_mass": mass,
            }
        )

    scored_attempts = sum(len(rows) for rows in attempts.values())
    successes = sum(row["success"] for rows in attempts.values() for row in rows)
    mixed_tasks = sum(row["mixed_outcomes"] for row in per_task)
    output_tokens_complete = output_tokens_complete and scored_attempts > 0
    tool_calls_complete = tool_calls_complete and scored_attempts > 0
    cost_complete = cost_complete and scored_attempts > 0
    effective_coverage = (
        (total_mass * total_mass) / (len(task_ids) * squared_mass)
        if squared_mass > 0 and task_ids
        else 0.0
    )
    signal_density = (
        1_000_000.0 * total_mass / total_output_tokens
        if output_tokens_complete and total_output_tokens > 0
        else None
    )

    family_summary = {}
    for name, values in sorted(family.items()):
        denominator = values["scored_attempts"]
        family_summary[name] = {
            **values,
            "success_rate": values["successes"] / denominator if denominator else None,
        }

    return {
        "task_count": len(task_ids),
        "scored_attempts": scored_attempts,
        "scientific_failures": scored_attempts - successes,
        "successes": successes,
        "success_rate": successes / scored_attempts if scored_attempts else None,
        "invalid_attempts": dict(sorted(invalid_counts.items())),
        "mixed_task_count": mixed_tasks,
        "mixed_task_fraction": mixed_tasks / len(task_ids) if task_ids else 0.0,
        "completion_advantage_mass": total_mass,
        "completion_signal_density_per_million_output_tokens": signal_density,
        "completion_signal_effective_task_coverage": effective_coverage,
        "output_token_accounting_complete": output_tokens_complete,
        "tool_call_accounting_complete": tool_calls_complete,
        "trajectory_cost_accounting_complete": cost_complete,
        "total_output_tokens": total_output_tokens if output_tokens_complete else None,
        "total_tool_calls": total_tool_calls if tool_calls_complete else None,
        "total_cost_usd": total_cost_usd if cost_complete else None,
        "task_family_summary": family_summary,
        "per_task": per_task,
    }


def input_digest(results_dir: Path, paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.relative_to(results_dir)).encode("utf-8"))
        digest.update(b"\0")
        if path.exists():
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        else:
            digest.update(b"missing")
    return digest.hexdigest()


def measure(checkout: Path, results_dir: Path, num_runs: int) -> dict:
    source = audit_checkout(checkout)
    domain_root = checkout / "state_bench" / "domains" / "customer_support"
    split = json.loads((domain_root / "splits" / "train_test.json").read_text())["splits"]
    task_ids = list(split["train"])
    task_types = {}
    for task_id in task_ids:
        task = json.loads((domain_root / "tasks" / f"{task_id}.json").read_text())
        task_types[task_id] = str(task["task_type"])

    attempts: dict[str, list[dict]] = defaultdict(list)
    invalid_counts: dict[str, int] = defaultdict(int)
    opened_paths = []
    for run_index in range(1, num_runs + 1):
        for task_id in task_ids:
            path = results_dir / f"run{run_index}" / f"{task_id}.json"
            opened_paths.append(path)
            attempt, invalid_reason = read_scored_attempt(path, task_id)
            if invalid_reason is not None:
                invalid_counts[invalid_reason] += 1
            else:
                assert attempt is not None
                attempts[task_id].append(attempt)

    summary = summarize_attempts(task_ids, task_types, attempts, invalid_counts)
    return {
        "schema_version": 1,
        "measurement_id": "state_bench_customer_support_starting_agent_v1",
        "source_revision": source["revision"],
        "domain": "customer_support",
        "split": "train",
        "requested_runs_per_task": num_runs,
        "expected_attempts": len(task_ids) * num_runs,
        "input_digest": input_digest(results_dir, opened_paths),
        "coordinate_definitions": {
            "completion_advantage_mass": (
                "Unnormalized leave-one-out absolute binary completion advantage mass "
                "within each task group."
            ),
            "completion_signal_density_per_million_output_tokens": (
                "Completion advantage mass per million agent output tokens; null "
                "unless output-token accounting is complete."
            ),
            "completion_signal_effective_task_coverage": (
                "Effective sample size of completion advantage mass divided by the 100 train tasks."
            ),
        },
        "summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkout", type=Path)
    parser.add_argument("results_dir", type=Path)
    parser.add_argument("--num-runs", type=int, default=5)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.num_runs < 2:
        raise SystemExit("--num-runs must be at least 2 to measure outcome variation")
    payload = measure(
        arguments.checkout.resolve(), arguments.results_dir.resolve(), arguments.num_runs
    )
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if arguments.output is None:
        print(serialized, end="")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(serialized, encoding="utf-8")


if __name__ == "__main__":
    main()
