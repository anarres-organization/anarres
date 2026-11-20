#!/usr/bin/env python3
"""Build matched customer-support candidate environments from development measurements."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_key(namespace: str, task_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"{namespace}\0{task_id}".encode()).hexdigest()
    return digest, task_id


def membership_hash(task_ids: list[str]) -> str:
    payload = "\n".join(sorted(task_ids)) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def proportional_quotas(task_types: dict[str, str], candidate_size: int) -> dict[str, int]:
    counts = Counter(task_types.values())
    if candidate_size < len(counts):
        raise ValueError("candidate size must retain at least one task from every task family")
    total = len(task_types)
    raw = {name: candidate_size * count / total for name, count in counts.items()}
    quotas = {name: max(1, math.floor(value)) for name, value in raw.items()}
    while sum(quotas.values()) > candidate_size:
        removable = [name for name in quotas if quotas[name] > 1]
        if not removable:
            raise ValueError("candidate size cannot satisfy the family coverage floor")
        name = min(removable, key=lambda item: (raw[item] - quotas[item], item))
        quotas[name] -= 1
    while sum(quotas.values()) < candidate_size:
        available = [name for name in quotas if quotas[name] < counts[name]]
        if not available:
            raise ValueError("candidate quotas exceed the source inventory")
        name = max(available, key=lambda item: (raw[item] - quotas[item], -counts[item], item))
        quotas[name] += 1
    return dict(sorted(quotas.items()))


def stratified_select(records: list[dict], quotas: dict[str, int], rank_key) -> list[str]:
    by_type: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        by_type[record["task_type"]].append(record)
    selected = []
    for task_type, quota in quotas.items():
        pool = sorted(by_type[task_type], key=rank_key)
        if len(pool) < quota:
            raise ValueError(f"task family {task_type} cannot satisfy its quota")
        selected.extend(record["task_id"] for record in pool[:quota])
    return sorted(selected)


def validate_measurement(measurement: dict, protocol: dict) -> list[dict]:
    if measurement.get("measurement_id") != "state_bench_customer_support_starting_agent_v1":
        raise ValueError("unsupported starting-agent measurement")
    if measurement.get("source_revision") != protocol["source"]["revision"]:
        raise ValueError("measurement source revision differs from the protocol")
    if measurement.get("domain") != "customer_support" or measurement.get("split") != "train":
        raise ValueError("candidate construction requires customer-support train measurements")
    summary = measurement["summary"]
    starting_agent = summary.get("starting_agent")
    if not isinstance(starting_agent, dict) or not starting_agent.get("model_name"):
        raise ValueError("measurement lacks one starting-agent identity")
    if summary["task_count"] != protocol["source"]["training_trajectory_count"]:
        raise ValueError("measurement task count differs from the protocol")
    if summary["scored_attempts"] != measurement["expected_attempts"]:
        raise ValueError("candidate construction requires complete scored measurements")
    if sum(summary["invalid_attempts"].values()) != 0:
        raise ValueError("candidate construction refuses infrastructure-invalid measurements")
    records = summary["per_task"]
    if len(records) != summary["task_count"]:
        raise ValueError("per-task measurement coverage is incomplete")
    ids = [record["task_id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("per-task measurement identities are not unique")
    runs = measurement["requested_runs_per_task"]
    for record in records:
        if record["scored_attempts"] != runs:
            raise ValueError(f"incomplete repeated measurement for {record['task_id']}")
        if not record.get("task_type"):
            raise ValueError(f"missing task family for {record['task_id']}")
        if record.get("success_rate") is None:
            raise ValueError(f"missing success rate for {record['task_id']}")
        if record.get("output_tokens") is None or record["output_tokens"] <= 0:
            raise ValueError(f"incomplete output-token accounting for {record['task_id']}")
        if record.get("completion_signal_density_per_million_output_tokens") is None:
            raise ValueError(f"missing signal density for {record['task_id']}")
    mixed_by_family = Counter(record["task_type"] for record in records if record["mixed_outcomes"])
    missing_signal = sorted(set(record["task_type"] for record in records) - set(mixed_by_family))
    if missing_signal:
        raise ValueError(
            "starting-agent measurement has no mixed-outcome task in family: "
            + ", ".join(missing_signal)
        )
    return records


def candidate_summary(task_ids: list[str], by_id: dict[str, dict]) -> dict:
    records = [by_id[task_id] for task_id in task_ids]
    total_mass = sum(record["completion_advantage_mass"] for record in records)
    total_tokens = sum(record["output_tokens"] for record in records)
    squared_mass = sum(record["completion_advantage_mass"] ** 2 for record in records)
    coverage = total_mass * total_mass / (len(records) * squared_mass) if squared_mass > 0 else 0.0
    return {
        "count": len(task_ids),
        "task_ids": sorted(task_ids),
        "membership_sha256": membership_hash(task_ids),
        "task_family_counts": dict(
            sorted(Counter(record["task_type"] for record in records).items())
        ),
        "starting_agent_success_rate": sum(record["success_rate"] for record in records)
        / len(records),
        "mixed_task_count": sum(bool(record["mixed_outcomes"]) for record in records),
        "completion_advantage_mass": total_mass,
        "completion_signal_density_per_million_output_tokens": (
            1_000_000.0 * total_mass / total_tokens
        ),
        "completion_signal_effective_task_coverage": coverage,
    }


def build_plan(measurement: dict, protocol: dict, candidate_size: int, random_seed: int) -> dict:
    records = validate_measurement(measurement, protocol)
    starting_agent = measurement["summary"]["starting_agent"]
    if candidate_size <= 0 or candidate_size >= len(records):
        raise ValueError("candidate size must be positive and smaller than the source pool")
    by_id = {record["task_id"]: record for record in records}
    task_types = {record["task_id"]: record["task_type"] for record in records}
    quotas = proportional_quotas(task_types, candidate_size)

    source_proportional = stratified_select(
        records,
        quotas,
        lambda record: stable_key("source-proportional-v1", record["task_id"]),
    )
    deterministic_random = sorted(
        records,
        key=lambda record: stable_key(f"random-v1:{random_seed}", record["task_id"]),
    )[:candidate_size]
    static_difficulty = stratified_select(
        records,
        quotas,
        lambda record: (abs(record["success_rate"] - 0.5), record["task_id"]),
    )
    policy_relative = stratified_select(
        records,
        quotas,
        lambda record: (
            -record["completion_signal_density_per_million_output_tokens"],
            -record["completion_advantage_mass"],
            record["task_id"],
        ),
    )

    memberships = {
        "source_proportional": source_proportional,
        "deterministic_random": sorted(record["task_id"] for record in deterministic_random),
        "static_difficulty": static_difficulty,
        "policy_relative": policy_relative,
    }
    candidates = {
        name: candidate_summary(task_ids, by_id) for name, task_ids in memberships.items()
    }
    membership_hashes = [candidate["membership_sha256"] for candidate in candidates.values()]
    if len(membership_hashes) != len(set(membership_hashes)):
        raise ValueError("candidate construction produced duplicate memberships")
    return {
        "schema_version": 1,
        "study_id": protocol["study_id"],
        "status": "DRAFT_CANDIDATE_PLAN__HELD_OUT_OUTCOMES_UNOPENED",
        "held_out_outcomes_opened": False,
        "candidate_size": candidate_size,
        "random_seed": random_seed,
        "task_family_quotas": quotas,
        "starting_agent": starting_agent,
        "predicted_choice": "policy_relative",
        "prediction_basis": (
            "Within-family ranking by starting-agent completion-signal density, "
            "with source-proportional family quotas."
        ),
        "candidates": candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--candidate-size", type=int, required=True)
    parser.add_argument("--random-seed", type=int, default=20261119)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise FileExistsError(arguments.output)
    measurement = json.loads(arguments.measurement.read_text(encoding="utf-8"))
    protocol = json.loads(arguments.protocol.read_text(encoding="utf-8"))
    result = build_plan(measurement, protocol, arguments.candidate_size, arguments.random_seed)
    result["inputs"] = {
        "measurement_sha256": sha256(arguments.measurement),
        "protocol_sha256": sha256(arguments.protocol),
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "candidate_size": result["candidate_size"],
                "candidates": list(result["candidates"]),
                "predicted_choice": result["predicted_choice"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
