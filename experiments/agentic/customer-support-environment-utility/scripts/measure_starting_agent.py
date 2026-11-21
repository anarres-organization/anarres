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


def optional_binary(record: dict, name: str) -> int | None:
    value = record.get(name)
    if value is None:
        return None
    if value not in (0, 1, False, True):
        raise ValueError(f"{name} must be binary when present")
    return int(value)


def agent_model_identity(record: dict) -> dict:
    model = record.get("agent_model")
    if not isinstance(model, dict):
        raise ValueError("agent_model metadata must be present on every scored trajectory")
    model_name = str(model.get("model_name", "")).strip()
    if not model_name:
        raise ValueError("agent_model.model_name must be non-empty")
    reasoning_level = model.get("reasoning_level")
    if reasoning_level is not None:
        reasoning_level = str(reasoning_level).strip() or None
    return {"model_name": model_name, "reasoning_level": reasoning_level}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_development_score(
    score_path: Path,
    trajectory_path: Path,
    expected_task_id: str,
    expected_run_index: int,
) -> tuple[dict | None, str | None]:
    if not score_path.exists():
        return None, "missing_development_score"
    try:
        record = json.loads(score_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, "malformed_development_score"
    if record.get("status") != "DEVELOPMENT_SCORE_COMPLETE":
        return None, "incomplete_development_score"
    if record.get("official_state_bench_compatible") is not False:
        raise ValueError(f"{score_path}: development sidecar has an invalid scope marker")
    if record.get("task_id") != expected_task_id or record.get("run_index") != expected_run_index:
        raise ValueError(f"{score_path}: development sidecar identity does not match")
    if record.get("trajectory", {}).get("sha256") != sha256(trajectory_path):
        raise ValueError(f"{score_path}: development sidecar trajectory hash does not match")
    contract = record.get("judge_contract")
    if not isinstance(contract, dict) or not contract.get("contract_sha256"):
        raise ValueError(f"{score_path}: development judge contract is missing")
    scores = record.get("scores")
    if not isinstance(scores, dict):
        return None, "malformed_development_score"
    return {"scores": scores, "judge_contract": contract}, None


def read_scored_attempt(
    path: Path,
    expected_task_id: str,
    *,
    run_index: int | None = None,
    development_score_path: Path | None = None,
) -> tuple[dict | None, str | None]:
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
    score_record = record
    judge_contract = None
    if development_score_path is not None:
        if run_index is None:
            raise ValueError("run_index is required with development score sidecars")
        development_score, error = read_development_score(
            development_score_path, path, expected_task_id, run_index
        )
        if error is not None:
            return None, error
        assert development_score is not None
        score_record = development_score["scores"]
        judge_contract = development_score["judge_contract"]
    outcome = score_record.get("task_completion_pass")
    if outcome not in (0, 1, False, True):
        return None, "unscored"
    return {
        "success": int(outcome),
        "input_tokens": numeric_field(record, "input_tokens", "token_usage", "input_tokens"),
        "output_tokens": numeric_field(record, "output_tokens", "token_usage", "output_tokens"),
        "tool_calls": numeric_field(record, "tool_calls", "efficiency", "tool_calls"),
        "tool_errors": numeric_field(record, "tool_errors", "efficiency", "tool_errors"),
        "redundant_calls": numeric_field(
            record, "redundant_calls", "efficiency", "redundant_calls"
        ),
        "cost_usd": numeric_field(record, "cost_usd", "token_usage", "total_cost_usd"),
        "state_requirements_met": optional_binary(score_record, "state_requirements_met"),
        "task_requirements_met": optional_binary(score_record, "task_requirements_met"),
        "ux_score": numeric_field(score_record, "ux_score", "ux_quality", "ux_score"),
        "agent_model": agent_model_identity(record),
        "development_judge_contract": judge_contract,
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
    model_identities = {
        json.dumps(row["agent_model"], sort_keys=True) for rows in attempts.values() for row in rows
    }
    if len(model_identities) != 1:
        raise ValueError("starting-agent measurements must use exactly one model identity")
    starting_agent = json.loads(next(iter(model_identities)))
    judge_contracts = {
        json.dumps(row["development_judge_contract"], sort_keys=True)
        for rows in attempts.values()
        for row in rows
        if row["development_judge_contract"] is not None
    }
    if len(judge_contracts) > 1:
        raise ValueError("development measurements must use exactly one judge contract")
    development_judge_contract = (
        json.loads(next(iter(judge_contracts))) if judge_contracts else None
    )
    per_task = []
    family = defaultdict(lambda: {"tasks": 0, "scored_attempts": 0, "successes": 0})
    total_mass = 0.0
    squared_mass = 0.0
    total_input_tokens = 0.0
    input_tokens_complete = True
    total_output_tokens = 0.0
    output_tokens_complete = True
    total_tool_calls = 0.0
    tool_calls_complete = True
    total_tool_errors = 0.0
    tool_errors_complete = True
    total_redundant_calls = 0.0
    redundant_calls_complete = True
    total_cost_usd = 0.0
    cost_complete = True
    state_task_pairs_complete = True
    state_pass_task_fail = 0
    task_pass_state_fail = 0
    ux_scores = []
    ux_complete = True

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

        task_input_tokens = [row["input_tokens"] for row in rows]
        task_output_tokens = [row["output_tokens"] for row in rows]
        task_tool_calls = [row["tool_calls"] for row in rows]
        task_tool_errors = [row["tool_errors"] for row in rows]
        task_redundant_calls = [row["redundant_calls"] for row in rows]
        task_costs = [row["cost_usd"] for row in rows]
        task_input_complete = bool(rows) and all(value is not None for value in task_input_tokens)
        task_output_complete = bool(rows) and all(value is not None for value in task_output_tokens)
        task_tools_complete = bool(rows) and all(value is not None for value in task_tool_calls)
        task_cost_complete = bool(rows) and all(value is not None for value in task_costs)
        task_output_total = (
            sum(value for value in task_output_tokens if value is not None)
            if task_output_complete
            else None
        )

        for row in rows:
            if row["input_tokens"] is None:
                input_tokens_complete = False
            else:
                total_input_tokens += row["input_tokens"]
            if row["output_tokens"] is None:
                output_tokens_complete = False
            else:
                total_output_tokens += row["output_tokens"]
            if row["tool_calls"] is None:
                tool_calls_complete = False
            else:
                total_tool_calls += row["tool_calls"]
            if row["tool_errors"] is None:
                tool_errors_complete = False
            else:
                total_tool_errors += row["tool_errors"]
            if row["redundant_calls"] is None:
                redundant_calls_complete = False
            else:
                total_redundant_calls += row["redundant_calls"]
            if row["cost_usd"] is None:
                cost_complete = False
            else:
                total_cost_usd += row["cost_usd"]
            state_met = row["state_requirements_met"]
            task_met = row["task_requirements_met"]
            if state_met is None or task_met is None:
                state_task_pairs_complete = False
            else:
                state_pass_task_fail += int(state_met == 1 and task_met == 0)
                task_pass_state_fail += int(task_met == 1 and state_met == 0)
            if row["ux_score"] is None:
                ux_complete = False
            else:
                ux_scores.append(row["ux_score"])

        per_task.append(
            {
                "task_id": task_id,
                "task_type": task_type,
                "scored_attempts": count,
                "successes": successes,
                "success_rate": successes / count if count else None,
                "mixed_outcomes": mixed,
                "completion_advantage_mass": mass,
                "completion_signal_density_per_million_output_tokens": (
                    1_000_000.0 * mass / task_output_total
                    if task_output_total is not None and task_output_total > 0
                    else None
                ),
                "output_tokens": task_output_total,
                "input_tokens": (
                    sum(value for value in task_input_tokens if value is not None)
                    if task_input_complete
                    else None
                ),
                "tool_calls": (
                    sum(value for value in task_tool_calls if value is not None)
                    if task_tools_complete
                    else None
                ),
                "tool_errors": (
                    sum(value for value in task_tool_errors if value is not None)
                    if bool(rows) and all(value is not None for value in task_tool_errors)
                    else None
                ),
                "redundant_calls": (
                    sum(value for value in task_redundant_calls if value is not None)
                    if bool(rows) and all(value is not None for value in task_redundant_calls)
                    else None
                ),
                "cost_usd": (
                    sum(value for value in task_costs if value is not None)
                    if task_cost_complete
                    else None
                ),
            }
        )

    scored_attempts = sum(len(rows) for rows in attempts.values())
    successes = sum(row["success"] for rows in attempts.values() for row in rows)
    mixed_tasks = sum(row["mixed_outcomes"] for row in per_task)
    input_tokens_complete = input_tokens_complete and scored_attempts > 0
    output_tokens_complete = output_tokens_complete and scored_attempts > 0
    tool_calls_complete = tool_calls_complete and scored_attempts > 0
    tool_errors_complete = tool_errors_complete and scored_attempts > 0
    redundant_calls_complete = redundant_calls_complete and scored_attempts > 0
    cost_complete = cost_complete and scored_attempts > 0
    state_task_pairs_complete = state_task_pairs_complete and scored_attempts > 0
    ux_complete = ux_complete and scored_attempts > 0
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
        "starting_agent": starting_agent,
        "development_judge_contract": development_judge_contract,
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
        "input_token_accounting_complete": input_tokens_complete,
        "output_token_accounting_complete": output_tokens_complete,
        "tool_call_accounting_complete": tool_calls_complete,
        "tool_error_accounting_complete": tool_errors_complete,
        "redundant_call_accounting_complete": redundant_calls_complete,
        "trajectory_cost_accounting_complete": cost_complete,
        "state_task_pair_accounting_complete": state_task_pairs_complete,
        "ux_accounting_complete": ux_complete,
        "total_input_tokens": total_input_tokens if input_tokens_complete else None,
        "total_output_tokens": total_output_tokens if output_tokens_complete else None,
        "total_tool_calls": total_tool_calls if tool_calls_complete else None,
        "total_tool_errors": total_tool_errors if tool_errors_complete else None,
        "total_redundant_calls": (total_redundant_calls if redundant_calls_complete else None),
        "total_cost_usd": total_cost_usd if cost_complete else None,
        "state_pass_task_fail_count": (state_pass_task_fail if state_task_pairs_complete else None),
        "task_pass_state_fail_count": (task_pass_state_fail if state_task_pairs_complete else None),
        "mean_ux_score": sum(ux_scores) / len(ux_scores) if ux_complete else None,
        "task_family_summary": family_summary,
        "per_task": per_task,
    }


def input_digest(paths: list[tuple[str, Path]]) -> str:
    digest = hashlib.sha256()
    for label, path in sorted(paths):
        digest.update(label.encode("utf-8"))
        digest.update(b"\0")
        if path.exists():
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        else:
            digest.update(b"missing")
    return digest.hexdigest()


def load_development_judge_decision(path: Path) -> dict:
    decision = json.loads(path.read_text(encoding="utf-8"))
    if decision.get("status") != "ACCEPTED_FOR_TRAIN_SIDE_DEVELOPMENT":
        raise ValueError("development judge was not accepted for train-side use")
    if decision.get("official_state_bench_compatible") is not False:
        raise ValueError("development judge decision has an invalid scope marker")
    if not decision.get("reviewed_all_disagreements"):
        raise ValueError("development judge disagreements were not fully reviewed")
    if not decision.get("judge_contract_sha256"):
        raise ValueError("development judge decision is missing its contract identity")
    return decision


def measure(
    checkout: Path,
    results_dir: Path,
    num_runs: int,
    development_scores_dir: Path | None = None,
    development_judge_decision_path: Path | None = None,
) -> dict:
    if (development_scores_dir is None) != (development_judge_decision_path is None):
        raise ValueError(
            "development sidecars and their accepted judge decision must be supplied together"
        )
    development_judge_decision = (
        load_development_judge_decision(development_judge_decision_path)
        if development_judge_decision_path is not None
        else None
    )
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
    opened_paths: list[tuple[str, Path]] = []
    if development_judge_decision_path is not None:
        opened_paths.append(("development_judge_decision", development_judge_decision_path))
    for run_index in range(1, num_runs + 1):
        for task_id in task_ids:
            path = results_dir / f"run{run_index}" / f"{task_id}.json"
            opened_paths.append((f"trajectory/run{run_index}/{task_id}.json", path))
            score_path = (
                development_scores_dir / f"run{run_index}" / f"{task_id}.json"
                if development_scores_dir is not None
                else None
            )
            if score_path is not None:
                opened_paths.append(
                    (f"development_score/run{run_index}/{task_id}.json", score_path)
                )
            attempt, invalid_reason = read_scored_attempt(
                path,
                task_id,
                run_index=run_index,
                development_score_path=score_path,
            )
            if invalid_reason is not None:
                invalid_counts[invalid_reason] += 1
            else:
                assert attempt is not None
                attempts[task_id].append(attempt)

    summary = summarize_attempts(task_ids, task_types, attempts, invalid_counts)
    if development_judge_decision is not None:
        measured_contract = summary["development_judge_contract"]
        if (
            measured_contract is None
            or measured_contract.get("contract_sha256")
            != (development_judge_decision["judge_contract_sha256"])
        ):
            raise ValueError("development sidecars do not match the accepted judge contract")
    return {
        "schema_version": 1,
        "measurement_id": "state_bench_customer_support_starting_agent_v1",
        "source_revision": source["revision"],
        "domain": "customer_support",
        "split": "train",
        "requested_runs_per_task": num_runs,
        "expected_attempts": len(task_ids) * num_runs,
        "input_digest": input_digest(opened_paths),
        "score_source": (
            "development_sidecars" if development_scores_dir is not None else "trajectory_scores"
        ),
        "development_judge_decision": development_judge_decision,
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
    parser.add_argument(
        "--development-scores-dir",
        type=Path,
        help="Development-only score sidecars bound to the input trajectories.",
    )
    parser.add_argument(
        "--development-judge-decision",
        type=Path,
        help="Human-reviewed acceptance record for the development judge.",
    )
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.num_runs < 2:
        raise SystemExit("--num-runs must be at least 2 to measure outcome variation")
    payload = measure(
        arguments.checkout.resolve(),
        arguments.results_dir.resolve(),
        arguments.num_runs,
        arguments.development_scores_dir.resolve()
        if arguments.development_scores_dir is not None
        else None,
        arguments.development_judge_decision.resolve()
        if arguments.development_judge_decision is not None
        else None,
    )
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if arguments.output is None:
        print(serialized, end="")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(serialized, encoding="utf-8")


if __name__ == "__main__":
    main()
