#!/usr/bin/env python3
"""Compute the frozen GPT-5.6 Sol repeated measurement from fresh grade receipts.

The estimands, cluster checks, and support gate are those of the earlier development
measurement, imported from its aggregator so that the two stay identical. This module
adds the Sol scoring rule, the readiness gate, and the abstention for an incomplete
queue.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from types import ModuleType
from typing import Any

STUDY_ROOT = Path(__file__).resolve().parent


def load(name: str, filename: str) -> ModuleType:
    specification = importlib.util.spec_from_file_location(name, STUDY_ROOT / filename)
    if specification is None or specification.loader is None:
        raise ImportError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


estimands = load("vero_probe_estimands", "aggregate_probe_measurements.py")

RECEIPT_SCHEMA = "anarres.formal-verification-codex-sol-grade-receipt.v1"
RESULT_SCHEMA = "anarres.formal-verification-codex-sol-measurement.v1"
OUTCOMES = ("scored", "integrity_failure", "infrastructure_failure")
RUN_OUTCOMES = (*OUTCOMES, "interrupted")
USAGE_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")


class AggregateError(ValueError):
    """Raised when the receipts do not satisfy the frozen analysis contract."""


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AggregateError(f"expected an object in {path.name}")
    return value


def collect_receipts(grades_root: Path) -> dict[str, dict[str, Any]]:
    receipts: dict[str, dict[str, Any]] = {}
    for path in sorted(grades_root.rglob("grade-receipt.json")):
        receipt = read_object(path)
        attempt_id = receipt.get("attempt_id")
        if not isinstance(attempt_id, str) or not attempt_id:
            raise AggregateError(f"missing attempt identity in {path.name}")
        if attempt_id in receipts:
            raise AggregateError(f"duplicate grade receipt for {attempt_id}")
        receipts[attempt_id] = receipt
    return receipts


def strict_reward(status: str, scoring: dict[str, Any]) -> int:
    """Score one status; the sensitivity rule names only its passes."""
    if status in scoring["strict_reward_one"]:
        return 1
    if "strict_reward_zero" in scoring and status not in scoring["strict_reward_zero"]:
        raise AggregateError(f"specification status {status!r} is not in the frozen scoring rule")
    return 0


def validate_receipt(entry: dict[str, Any], receipt: dict[str, Any], analysis: dict) -> None:
    attempt_id = entry["attempt_id"]
    if receipt.get("schema_version") != RECEIPT_SCHEMA:
        raise AggregateError(f"{attempt_id} has an unexpected receipt schema")
    for field in ("attempt_id", "benchmark_id", "mode", "task_id", "replicate"):
        if receipt.get(field) != entry[field]:
            raise AggregateError(f"{attempt_id} disagrees on {field}")
    if receipt.get("outcome") not in OUTCOMES:
        raise AggregateError(f"{attempt_id} has an unknown outcome")
    if not isinstance(receipt.get("authorization_sha256"), str):
        raise AggregateError(f"{attempt_id} names no execution authorization")
    validate_runs(attempt_id, receipt, analysis)
    if receipt["outcome"] == "infrastructure_failure":
        return
    materialization = receipt.get("materialization") or {}
    if not all(
        isinstance(materialization.get(field), str)
        for field in ("task_tree_sha256", "instruction_sha256")
    ):
        raise AggregateError(f"{attempt_id} does not identify its materialized task")
    if receipt.get("specifications_total") != entry["expected_specifications"]:
        raise AggregateError(f"{attempt_id} has an unexpected specification count")
    tokens = receipt.get("model_tokens")
    if not isinstance(tokens, int) or tokens <= 0:
        raise AggregateError(f"{attempt_id} has invalid model-token usage")
    if tokens != receipt.get("input_tokens", -1) + receipt.get("output_tokens", -1):
        raise AggregateError(f"{attempt_id} model tokens are not input plus output tokens")
    records = receipt.get("per_specification")
    if receipt["outcome"] == "integrity_failure":
        if records:
            raise AggregateError(f"{attempt_id} is an integrity failure with graded records")
        if not receipt.get("integrity_errors"):
            raise AggregateError(f"{attempt_id} is an integrity failure without a reason")
        return
    if not isinstance(records, list) or len(records) != entry["expected_specifications"]:
        raise AggregateError(f"{attempt_id} has an unexpected number of specification records")
    scoring = analysis["specification_scoring"]
    for record in records:
        if record.get("strict_reward") != strict_reward(record.get("status"), scoring):
            raise AggregateError(f"{attempt_id} disagrees with the frozen scoring rule")


def validate_runs(attempt_id: str, receipt: dict[str, Any], analysis: dict[str, Any]) -> None:
    """Only infrastructure may end a run early, and only the frozen retries may follow."""
    runs = receipt.get("runs")
    if not isinstance(runs, list) or not 1 <= len(runs) <= analysis["maximum_runs_per_entry"]:
        raise AggregateError(f"{attempt_id} has an invalid number of runs")
    for number, run in enumerate(runs, start=1):
        if run.get("run") != number or run.get("outcome") not in RUN_OUTCOMES:
            raise AggregateError(f"{attempt_id} has an invalid run record")
        if number < len(runs) and run["outcome"] not in ("infrastructure_failure", "interrupted"):
            raise AggregateError(f"{attempt_id} retried a scientific outcome")
        if run.get("kind") == "regrade":
            previous = runs[number - 2] if number > 1 else None
            if previous is None or previous["outcome"] != "infrastructure_failure":
                raise AggregateError(f"{attempt_id} regraded without a failed grading")
            if any(run[field] for field in USAGE_FIELDS):
                raise AggregateError(f"{attempt_id} charged model tokens to a regrade")
        elif run.get("kind") != "attempt":
            raise AggregateError(f"{attempt_id} has an unknown run kind")
    final = runs[-1]["outcome"]
    if (final if final != "interrupted" else "infrastructure_failure") != receipt["outcome"]:
        raise AggregateError(f"{attempt_id} disagrees with its final run")
    if receipt["outcome"] == "infrastructure_failure":
        return
    policy_run = next(run for run in reversed(runs) if run["kind"] == "attempt")
    if policy_run["run_id"] != receipt.get("run_id") or any(
        policy_run[field] != receipt.get(field) for field in USAGE_FIELDS
    ):
        raise AggregateError(f"{attempt_id} does not measure the run it graded")


def incomplete_entries(queue: dict[str, Any], receipts: dict[str, Any]) -> list[str]:
    return [
        entry["attempt_id"]
        for entry in queue["attempts"]
        if entry["attempt_id"] not in receipts
        or receipts[entry["attempt_id"]].get("outcome") == "infrastructure_failure"
    ]


def cell_rewards(
    records: list[tuple[dict[str, Any], dict[str, Any]]], scoring: dict[str, Any]
) -> tuple[list[str], list[dict[str, int]]]:
    """Return the cell's specification keys and each attempt's rewards over them."""
    graded = [receipt for _, receipt in records if receipt["outcome"] == "scored"]
    keys: list[str] | None = None
    for receipt in graded:
        attempt_keys = sorted(
            f"{record['module']}::{record['specification']}"
            for record in receipt["per_specification"]
        )
        if len(set(attempt_keys)) != len(attempt_keys):
            raise AggregateError(f"duplicate specification in {receipt['attempt_id']}")
        if keys is not None and attempt_keys != keys:
            raise AggregateError(f"specification identities drifted in {receipt['task_id']}")
        keys = attempt_keys
    if keys is None:
        # Every attempt in the cell failed integrity, so none was graded.
        keys = [
            f"unidentified::{index}" for index in range(records[0][0]["expected_specifications"])
        ]
    rewards = []
    for _, receipt in sorted(records, key=lambda pair: pair[0]["replicate"]):
        if receipt["outcome"] == "integrity_failure":
            rewards.append(dict.fromkeys(keys, 0))
            continue
        rewards.append(
            {
                f"{record['module']}::{record['specification']}": strict_reward(
                    record["status"], scoring
                )
                for record in receipt["per_specification"]
            }
        )
    return keys, rewards


def measure(
    grouped: dict[tuple[str, str], list[tuple[dict[str, Any], dict[str, Any]]]],
    analysis: dict[str, Any],
    scoring: dict[str, Any],
) -> dict[str, Any]:
    attempts = analysis["attempts_per_group"]
    by_mode: dict[str, Any] = {}
    groups_by_mode: dict[str, dict[str, list[dict[str, Any]]]] = {}
    pooled_passes = 0
    pooled_trials = 0
    repositories_with_coverage: set[str] = set()
    for mode in sorted({mode for mode, _ in grouped}):
        groups_by_repository: dict[str, list[dict[str, Any]]] = {}
        summaries = {}
        for (record_mode, benchmark_id), records in sorted(grouped.items()):
            if record_mode != mode:
                continue
            if len(records) != attempts:
                raise AggregateError(f"{benchmark_id}:{mode} has {len(records)} attempts")
            keys, rewards = cell_rewards(records, scoring)
            tokens = sum(receipt["model_tokens"] for _, receipt in records)
            groups = []
            for key in keys:
                successes = sum(reward[key] for reward in rewards)
                groups.append(
                    {
                        "repository": benchmark_id,
                        "specification": key,
                        "successes": successes,
                        "attempts": attempts,
                        "advantage_mass": estimands.advantage_mass(successes, attempts),
                        "model_tokens": tokens / len(keys),
                    }
                )
            groups_by_repository[benchmark_id] = groups
            passed = sum(group["successes"] for group in groups)
            trials = len(keys) * attempts
            pooled_passes += passed
            pooled_trials += trials
            if passed:
                repositories_with_coverage.add(benchmark_id)
            reliability = Counter(group["successes"] for group in groups)
            summaries[benchmark_id] = {
                **estimands.coordinates(groups),
                "strict_successes": passed,
                "strict_trials": trials,
                "strict_success_rate": passed / trials,
                "union_coverage": sum(group["successes"] > 0 for group in groups) / len(keys),
                "specifications_by_successes": {
                    str(count): reliability.get(count, 0) for count in range(attempts + 1)
                },
            }
        mode_groups = [group for groups in groups_by_repository.values() for group in groups]
        groups_by_mode[mode] = groups_by_repository
        by_mode[mode] = {
            "coordinates": estimands.coordinates(mode_groups),
            "repositories": summaries,
            "cluster_sensitivity": estimands.cluster_sensitivity(groups_by_repository, analysis),
        }

    total_mixed = sum(
        int(measurement["coordinates"]["mixed_specification_groups"])
        for measurement in by_mode.values()
    )
    rate = pooled_passes / pooled_trials
    gates = analysis["admission_summary"]
    support = {
        "repositories_with_nonzero_verified_coverage": len(repositories_with_coverage),
        "mixed_specification_groups": total_mixed,
        "pooled_strict_successes": pooled_passes,
        "pooled_strict_trials": pooled_trials,
        "pooled_strict_success_rate": rate,
        "passes_support_gate": (
            len(repositories_with_coverage)
            >= gates["minimum_repositories_with_nonzero_verified_coverage"]
            and total_mixed >= gates["minimum_mixed_specification_groups"]
            and gates["minimum_pooled_strict_success"]
            <= rate
            <= gates["maximum_pooled_strict_success"]
        ),
    }

    readiness_contract = analysis["readiness_gate"]
    mixed_repositories = {
        mode: sorted(
            repository
            for repository, groups in repositories.items()
            if any(group["advantage_mass"] > 0 for group in groups)
        )
        for mode, repositories in groups_by_mode.items()
    }
    repositories = sorted({repository for _, repository in grouped})
    mixed_without = {
        held_out: sum(
            group["advantage_mass"] > 0
            for groups in groups_by_mode.values()
            for repository, repository_groups in groups.items()
            if repository != held_out
            for group in repository_groups
        )
        for held_out in repositories
    }
    readiness = {
        "repositories_with_mixed_groups_by_mode": mixed_repositories,
        "mixed_groups_after_leaving_out_repository": mixed_without,
        "passes_readiness_gate": (
            (support["passes_support_gate"] or not readiness_contract["requires_admission_summary"])
            and all(
                len(names)
                >= readiness_contract["minimum_repositories_with_mixed_groups_in_each_mode"]
                for names in mixed_repositories.values()
            )
            and min(mixed_without.values())
            >= readiness_contract[
                "minimum_mixed_specification_groups_after_leaving_out_any_repository"
            ]
        ),
    }
    return {"measurements_by_mode": by_mode, "support": support, "readiness": readiness}


def cost_summary(
    entries: list[dict[str, Any]], receipts: dict[str, Any], analysis: dict[str, Any]
) -> dict[str, Any]:
    prices = analysis["cost_reporting"]["planning_prices_usd_per_million_tokens"]
    measured = [receipts[entry["attempt_id"]] for entry in entries]

    def usd(usage: dict[str, Any]) -> float:
        cached = usage["cached_input_tokens"]
        return (
            (usage["input_tokens"] - cached) * prices["uncached_input"]
            + cached * prices["cached_input"]
            + usage["output_tokens"] * prices["output"]
        ) / 1_000_000

    passed = sum(
        record["strict_reward"] for receipt in measured for record in receipt["per_specification"]
    )
    tokens = sum(receipt["model_tokens"] for receipt in measured)
    return {
        "model_tokens": tokens,
        "mean_model_tokens_per_attempt": tokens / len(measured),
        "model_tokens_per_strict_success": None if passed == 0 else tokens / passed,
        "planning_usd": sum(usd(receipt) for receipt in measured),
        # Runs lost to infrastructure cost tokens without entering the measurement.
        "planning_usd_including_retried_runs": sum(
            usd(run) for receipt in measured for run in receipt["runs"]
        ),
        "stop_reasons": dict(sorted(Counter(r["stop_reason"] for r in measured).items())),
        "agent_wall_seconds": sum(receipt["agent_wall_seconds"] for receipt in measured),
    }


def run_counts(ledgers: dict[str, list[dict[str, Any]]], analysis: dict[str, Any]) -> dict:
    """Every run on the ledger, so infrastructure failures are reported apart from outcomes."""
    runs = [run for entry_runs in ledgers.values() for run in entry_runs]
    counts = Counter(run["outcome"] for run in runs)
    prices = analysis["cost_reporting"]["planning_prices_usd_per_million_tokens"]
    return {
        **{f"{outcome}_runs": counts.get(outcome, 0) for outcome in RUN_OUTCOMES},
        "regrade_runs": sum(run["kind"] == "regrade" for run in runs),
        "interrupted_attempts": sorted(
            attempt_id
            for attempt_id, entry_runs in ledgers.items()
            if any(run["outcome"] == "interrupted" for run in entry_runs)
        ),
        # Interrupted runs reported no tokens, so they are counted, not priced.
        "recorded_planning_usd": sum(
            (
                (run["input_tokens"] - run["cached_input_tokens"]) * prices["uncached_input"]
                + run["cached_input_tokens"] * prices["cached_input"]
                + run["output_tokens"] * prices["output"]
            )
            / 1_000_000
            for run in runs
        ),
    }


def aggregate(
    queue: dict[str, Any],
    analysis: dict[str, Any],
    receipts: dict[str, Any],
    *,
    spend_ceiling_stopped: bool = False,
    ledgers: dict[str, list[dict[str, Any]]] | None = None,
    task_digests: dict[str, dict[str, str]] | None = None,
) -> dict:
    """Aggregate the receipts; ``ledgers`` adds runs of entries that have no receipt."""
    entries = queue["attempts"]
    expected = {entry["attempt_id"] for entry in entries}
    extra = sorted(set(receipts) - expected)
    if extra:
        raise AggregateError(f"receipts outside the frozen queue: {extra}")
    for entry in entries:
        if entry["attempt_id"] in receipts:
            validate_receipt(entry, receipts[entry["attempt_id"]], analysis)
    authorizations = sorted({receipt["authorization_sha256"] for receipt in receipts.values()})
    if len(authorizations) > 1:
        raise AggregateError("the receipts come from more than one execution authorization")
    tasks: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for receipt in receipts.values():
        if receipt["outcome"] != "infrastructure_failure":
            identity = receipt["materialization"]
            tasks[receipt["task_id"]].add(
                (identity["task_tree_sha256"], identity["instruction_sha256"])
            )
    if any(len(identities) > 1 for identities in tasks.values()):
        raise AggregateError("replicates of one task were materialized differently")
    for task_id, identities in tasks.items():
        frozen = (task_digests or {}).get(task_id)
        if task_digests is not None and (
            frozen is None
            or identities != {(frozen["task_tree_sha256"], frozen["instruction_sha256"])}
        ):
            raise AggregateError(f"{task_id} was not materialized as frozen")
    result: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA,
        "queue_id": queue["queue_id"],
        "analysis_id": analysis["analysis_id"],
        "authorization_sha256": authorizations[0] if authorizations else None,
        "attempts": len(entries),
        "runs": run_counts(
            {attempt_id: receipt["runs"] for attempt_id, receipt in receipts.items()}
            if ledgers is None
            else ledgers,
            analysis,
        ),
    }
    incomplete = incomplete_entries(queue, receipts)
    if incomplete:
        return {
            **result,
            "decision": "abstain",
            "abstention_reason": "spend_ceiling_reached"
            if spend_ceiling_stopped
            else "infrastructure_incomplete",
            "incomplete_attempts": incomplete,
        }

    grouped: dict[tuple[str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for entry in entries:
        grouped[(entry["mode"], entry["benchmark_id"])].append(
            (entry, receipts[entry["attempt_id"]])
        )
    outcomes = Counter(receipts[entry["attempt_id"]]["outcome"] for entry in entries)
    primary = measure(grouped, analysis, analysis["specification_scoring"])
    sensitivity = measure(grouped, analysis, analysis["sensitivity_scoring"])
    statuses = Counter(
        record["status"]
        for entry in entries
        for record in receipts[entry["attempt_id"]]["per_specification"]
    )
    ready = primary["readiness"]["passes_readiness_gate"]
    return {
        **result,
        "attempt_outcomes": {outcome: outcomes.get(outcome, 0) for outcome in OUTCOMES[:2]},
        "specification_statuses": dict(sorted(statuses.items())),
        **primary,
        "sensitivity": {
            "name": analysis["sensitivity_scoring"]["name"],
            "support": sensitivity["support"],
            "readiness": sensitivity["readiness"],
        },
        "cost": cost_summary(entries, receipts, analysis),
        "decision": "ready" if ready else "abstain",
        "abstention_reason": None if ready else "readiness_gate_failed",
    }


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_ledger(grades_root: Path, receipts: dict[str, Any], runner: ModuleType) -> None:
    """Each receipt must restate the run records the runner left beside it."""
    for attempt_id, receipt in receipts.items():
        runs = runner.ledger(grades_root / attempt_id)
        recorded = [
            {field: run[field] for field in ("run", "kind", "run_id", "outcome", *USAGE_FIELDS)}
            for run in runs
        ]
        if recorded != receipt["runs"]:
            raise AggregateError(f"{attempt_id} disagrees with its run records")


def bound_inputs(
    protocol_path: Path, queue_path: Path, authorization_path: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return the frozen queue, analysis, and input digests once they agree."""
    if protocol_path.resolve().parent != STUDY_ROOT:
        raise AggregateError("the protocol must be validated in this study directory")
    protocol = read_object(protocol_path)
    load("vero_codex_sol_aggregate_validator", "validate_codex_sol_probe_protocol.py").validate(
        protocol, STUDY_ROOT
    )
    panel_path = STUDY_ROOT / protocol["source"]["development_panel"]
    queue = read_object(queue_path)
    expected = load("vero_codex_sol_aggregate_builder", "build_probe_queue.py").build_queue(
        protocol,
        read_object(panel_path),
        protocol_sha256=digest(protocol_path),
        panel_sha256=digest(panel_path),
    )
    if queue != expected:
        raise AggregateError("the queue does not match the frozen protocol")
    authorization = read_object(authorization_path)
    if (
        authorization.get("schema_version")
        != "anarres.formal-verification-codex-sol-execution-authorization.v1"
        or authorization.get("authorized") is not True
        or authorization.get("protocol_sha256") != digest(protocol_path)
        or authorization.get("queue_sha256") != digest(queue_path)
    ):
        raise AggregateError("the authorization record does not bind this protocol and queue")
    for field in ("spend_ceiling_usd", "per_attempt_reserve_usd"):
        value = authorization.get(field)
        if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
            raise AggregateError(f"the authorization record has no positive {field}")
    if authorization["per_attempt_reserve_usd"] > authorization["spend_ceiling_usd"]:
        raise AggregateError("the per-attempt reserve exceeds the spend ceiling")
    analysis_path = STUDY_ROOT / protocol["measurement"]["analysis_contract"]
    digests = {
        "protocol_sha256": digest(protocol_path),
        "queue_sha256": digest(queue_path),
        "analysis_sha256": digest(analysis_path),
        "authorization_sha256": digest(authorization_path),
        "task_digests": protocol["probe_design"]["task_digests"],
    }
    return queue, read_object(analysis_path), digests


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--grades", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise AggregateError("--output must not exist")
    runner = load("vero_codex_sol_authorization_validator", "run_codex_sol_queue_item.py")
    try:
        runner.validate_committed_authorization(args.authorization)
    except runner.QueueItemError as error:
        raise AggregateError(str(error)) from error
    queue, analysis, digests = bound_inputs(args.protocol, args.queue, args.authorization)
    task_digests = digests.pop("task_digests")
    receipt_paths = sorted(args.grades.rglob("grade-receipt.json"))
    inputs = {
        **digests,
        "receipt_sha256": {path.parent.name: digest(path) for path in receipt_paths},
    }
    runner = load("vero_codex_sol_aggregate_runner", "run_codex_sol_queue_item.py")
    entry_ids = {entry["attempt_id"] for entry in queue["attempts"]}
    ledgers = None
    try:
        ledgers = {
            path.name: runner.ledger(path)
            for path in sorted(args.grades.iterdir())
            if path.is_dir() and path.name in entry_ids
        }
        receipts = collect_receipts(args.grades)
        validate_ledger(args.grades, receipts, runner)
        result = aggregate(
            queue,
            analysis,
            receipts,
            spend_ceiling_stopped=(args.grades / "spend-ceiling-stop.json").exists(),
            ledgers=ledgers,
            task_digests=task_digests,
        )
        if result["authorization_sha256"] not in (None, digests["authorization_sha256"]):
            raise AggregateError("the receipts name a different execution authorization")
    except (AggregateError, runner.QueueItemError, KeyError, TypeError, ValueError) as error:
        # A receipt set the frozen rules reject is released as an abstention, not dropped.
        result = {
            "schema_version": RESULT_SCHEMA,
            "queue_id": queue["queue_id"],
            "analysis_id": analysis["analysis_id"],
            "decision": "abstain",
            "abstention_reason": "aggregate_rejected",
            "rejection": f"{type(error).__name__}: {error}",
        }
        if ledgers is not None:
            result["runs"] = run_counts(ledgers, analysis)
    result["inputs"] = inputs
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote the {result['decision']} GPT-5.6 Sol measurement to {args.output}")


if __name__ == "__main__":
    main()
