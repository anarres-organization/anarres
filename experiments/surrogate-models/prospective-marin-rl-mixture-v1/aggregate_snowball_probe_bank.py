#!/usr/bin/env python3
"""Aggregate a source-stratified Snowball starting-policy probe bank."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, pvariance


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"attempt line {line_number} is invalid JSON") from error
        if not isinstance(row, dict):
            raise ValueError(f"attempt line {line_number} must contain an object")
        rows.append(row)
    if not rows:
        raise ValueError("probe bank contains no attempts")
    return rows


def finite_number(value: object, name: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


def validate_metadata(metadata: dict) -> None:
    required = {
        "schema_version",
        "study_id",
        "probe_bank_id",
        "policy_id",
        "policy_revision",
        "group_size",
        "temperature",
        "max_new_tokens",
        "source_revisions",
    }
    if set(metadata) != required:
        raise ValueError("probe metadata fields differ from the frozen contract")
    if metadata["schema_version"] != "anarres.snowball-probe-bank-metadata.v1":
        raise ValueError("unsupported probe-bank metadata schema")
    if not isinstance(metadata["group_size"], int) or metadata["group_size"] < 2:
        raise ValueError("group size must be an integer of at least two")
    if finite_number(metadata["temperature"], "temperature") < 0:
        raise ValueError("temperature must be non-negative")
    if not isinstance(metadata["max_new_tokens"], int) or metadata["max_new_tokens"] <= 0:
        raise ValueError("maximum new tokens must be a positive integer")
    revisions = metadata["source_revisions"]
    if not isinstance(revisions, dict) or not revisions:
        raise ValueError("source revisions must be a non-empty mapping")
    if any(not source or not revision for source, revision in revisions.items()):
        raise ValueError("source identities and revisions must be non-empty")


def validate_attempt(row: dict, metadata: dict) -> None:
    required = {
        "attempt_id",
        "probe_bank_id",
        "source_id",
        "task_id",
        "prompt_group_id",
        "sample_index",
        "policy_version",
        "sampling_probability",
        "generated_tokens",
        "loss_eligible_tokens",
        "reward",
        "verifier_status",
        "admission_status",
        "infrastructure_status",
        "termination_reason",
        "tool_call_status",
        "trace_digest",
    }
    if set(row) != required:
        raise ValueError(
            f"attempt {row.get('attempt_id', '<unknown>')} fields differ from the contract"
        )
    if row["probe_bank_id"] != metadata["probe_bank_id"]:
        raise ValueError(f"attempt {row['attempt_id']} belongs to another probe bank")
    if row["policy_version"] != metadata["policy_revision"]:
        raise ValueError(f"attempt {row['attempt_id']} uses another policy revision")
    if row["source_id"] not in metadata["source_revisions"]:
        raise ValueError(f"attempt {row['attempt_id']} uses an undeclared source")
    if not isinstance(row["sample_index"], int) or row["sample_index"] < 0:
        raise ValueError(f"attempt {row['attempt_id']} has an invalid sample index")
    probability = finite_number(row["sampling_probability"], "sampling probability")
    if not 0 < probability <= 1:
        raise ValueError(f"attempt {row['attempt_id']} has an invalid sampling probability")
    if not isinstance(row["generated_tokens"], int) or row["generated_tokens"] < 0:
        raise ValueError(f"attempt {row['attempt_id']} has invalid generated tokens")
    if (
        not isinstance(row["loss_eligible_tokens"], int)
        or row["loss_eligible_tokens"] < 0
        or row["loss_eligible_tokens"] > row["generated_tokens"]
    ):
        raise ValueError(f"attempt {row['attempt_id']} has invalid loss-eligible tokens")
    if row["verifier_status"] not in {"valid", "invalid", "unavailable"}:
        raise ValueError(f"attempt {row['attempt_id']} has an unknown verifier status")
    if row["infrastructure_status"] not in {"valid", "invalid"}:
        raise ValueError(f"attempt {row['attempt_id']} has an unknown infrastructure status")
    if row["admission_status"] not in {"admitted", "excluded"}:
        raise ValueError(f"attempt {row['attempt_id']} has an unknown admission status")
    scientifically_valid = (
        row["infrastructure_status"] == "valid" and row["verifier_status"] == "valid"
    )
    if scientifically_valid:
        reward = finite_number(row["reward"], f"reward {row['attempt_id']}")
        if not 0 <= reward <= 1:
            raise ValueError(f"reward lies outside [0, 1] for {row['attempt_id']}")
    elif row["reward"] is not None:
        raise ValueError(f"invalid attempt {row['attempt_id']} must not carry a scientific reward")
    if not scientifically_valid and row["admission_status"] != "excluded":
        raise ValueError(f"invalid attempt {row['attempt_id']} must be excluded from the loss")
    if row["admission_status"] == "admitted" and row["loss_eligible_tokens"] <= 0:
        raise ValueError(f"admitted attempt {row['attempt_id']} has no loss-eligible tokens")
    if row["admission_status"] == "excluded" and row["loss_eligible_tokens"] != 0:
        raise ValueError(f"excluded attempt {row['attempt_id']} carries loss-eligible tokens")
    for field in (
        "attempt_id",
        "task_id",
        "prompt_group_id",
        "termination_reason",
        "tool_call_status",
        "trace_digest",
    ):
        if not isinstance(row[field], str) or not row[field]:
            raise ValueError(f"attempt field {field} must be non-empty")


def group_measurement(rows: list[dict], metadata: dict) -> dict:
    sample_indices = [row["sample_index"] for row in rows]
    if sorted(sample_indices) != list(range(metadata["group_size"])):
        raise ValueError(
            f"prompt group {rows[0]['prompt_group_id']} does not cover the frozen sample indices"
        )
    if len({row["task_id"] for row in rows}) != 1 or len({row["source_id"] for row in rows}) != 1:
        raise ValueError(f"prompt group {rows[0]['prompt_group_id']} mixes tasks or sources")
    if sum(row["generated_tokens"] for row in rows) <= 0:
        raise ValueError(f"prompt group {rows[0]['prompt_group_id']} generated no tokens")

    valid_rows = [
        row
        for row in rows
        if row["infrastructure_status"] == "valid" and row["verifier_status"] == "valid"
    ]
    raw_advantage: dict[str, float] = {}
    if len(valid_rows) >= 2:
        rewards = [float(row["reward"]) for row in valid_rows]
        for index, row in enumerate(valid_rows):
            other_mean = (sum(rewards) - rewards[index]) / (len(rewards) - 1)
            raw_advantage[row["attempt_id"]] = abs(rewards[index] - other_mean)
    admitted_mass = sum(
        raw_advantage.get(row["attempt_id"], 0.0)
        for row in valid_rows
        if row["admission_status"] == "admitted"
    )
    rewards = [float(row["reward"]) for row in valid_rows]
    return {
        "source_id": rows[0]["source_id"],
        "task_id": rows[0]["task_id"],
        "prompt_group_id": rows[0]["prompt_group_id"],
        "attempts": len(rows),
        "valid_rewards": len(valid_rows),
        "admitted_attempts": sum(row["admission_status"] == "admitted" for row in valid_rows),
        "infrastructure_invalid_attempts": sum(
            row["infrastructure_status"] != "valid" for row in rows
        ),
        "verifier_invalid_attempts": sum(
            row["infrastructure_status"] == "valid" and row["verifier_status"] != "valid"
            for row in rows
        ),
        "trace_failure_attempts": sum(
            row["tool_call_status"] not in {"not_applicable", "valid"} for row in rows
        ),
        "reward_min": min(rewards) if rewards else None,
        "reward_max": max(rewards) if rewards else None,
        "reward_mean": mean(rewards) if rewards else None,
        "admitted_advantage_mass": admitted_mass,
        "generated_tokens": sum(row["generated_tokens"] for row in rows),
        "loss_eligible_tokens": sum(row["loss_eligible_tokens"] for row in valid_rows),
    }


def coordinates(groups: list[dict]) -> dict:
    masses = [group["admitted_advantage_mass"] for group in groups]
    total_mass = sum(masses)
    total_tokens = sum(group["generated_tokens"] for group in groups)
    squared_mass = sum(mass * mass for mass in masses)
    return {
        "usable_signal_density_per_million_generated_tokens": 1_000_000 * total_mass / total_tokens,
        "effective_prompt_coverage": (
            0.0 if squared_mass == 0 else total_mass * total_mass / squared_mass / len(groups)
        ),
        "total_admitted_advantage_mass": total_mass,
        "generated_tokens": total_tokens,
        "prompt_groups": len(groups),
    }


def aggregate(metadata: dict, attempts: list[dict]) -> dict:
    validate_metadata(metadata)
    seen_attempts = set()
    prompt_group_sources: dict[str, str] = {}
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in attempts:
        validate_attempt(row, metadata)
        if row["attempt_id"] in seen_attempts:
            raise ValueError(f"duplicate attempt identity {row['attempt_id']}")
        seen_attempts.add(row["attempt_id"])
        prior_source = prompt_group_sources.setdefault(row["prompt_group_id"], row["source_id"])
        if prior_source != row["source_id"]:
            raise ValueError(f"prompt group {row['prompt_group_id']} is reused across sources")
        grouped[(row["source_id"], row["prompt_group_id"])].append(row)

    groups = [group_measurement(rows, metadata) for _, rows in sorted(grouped.items())]
    source_groups: dict[str, list[dict]] = defaultdict(list)
    for group in groups:
        source_groups[group["source_id"]].append(group)
    if set(source_groups) != set(metadata["source_revisions"]):
        missing = sorted(set(metadata["source_revisions"]) - set(source_groups))
        raise ValueError(f"probe bank has no prompt groups for sources: {', '.join(missing)}")

    sources = []
    for source_id in sorted(source_groups):
        rows = source_groups[source_id]
        rewards = [group["reward_mean"] for group in rows if group["reward_mean"] is not None]
        attempts_count = sum(group["attempts"] for group in rows)
        sources.append(
            {
                "source_id": source_id,
                "source_revision": metadata["source_revisions"][source_id],
                "coordinates": coordinates(rows),
                "validity": {
                    "reward_attempt_fraction": sum(group["valid_rewards"] for group in rows)
                    / attempts_count,
                    "infrastructure_invalid_fraction": sum(
                        group["infrastructure_invalid_attempts"] for group in rows
                    )
                    / attempts_count,
                    "verifier_invalid_fraction": sum(
                        group["verifier_invalid_attempts"] for group in rows
                    )
                    / attempts_count,
                    "trace_failure_fraction": sum(group["trace_failure_attempts"] for group in rows)
                    / attempts_count,
                },
                "reward_distribution": {
                    "group_mean_count": len(rewards),
                    "group_mean": mean(rewards) if rewards else None,
                    "group_variance": pvariance(rewards) if rewards else None,
                    "group_min": min(rewards) if rewards else None,
                    "group_max": max(rewards) if rewards else None,
                },
            }
        )

    result = {
        "schema_version": "anarres.snowball-probe-bank.v1",
        "study_id": metadata["study_id"],
        "probe_bank_id": metadata["probe_bank_id"],
        "policy_id": metadata["policy_id"],
        "policy_revision": metadata["policy_revision"],
        "probe_contract": {
            "group_size": metadata["group_size"],
            "temperature": metadata["temperature"],
            "max_new_tokens": metadata["max_new_tokens"],
            "advantage_estimator": "leave-one-out-unnormalized-absolute",
        },
        "sources": sources,
        "groups": groups,
        "boundary": (
            "Source-level prediction-time evidence only. Candidate coordinates require "
            "a separately frozen reweighting and prompt-selection rule."
        ),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--attempts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise FileExistsError(arguments.output)
    metadata = json.loads(arguments.metadata.read_text(encoding="utf-8"))
    result = aggregate(metadata, read_jsonl(arguments.attempts))
    result["inputs"] = {
        "metadata_sha256": sha256(arguments.metadata),
        "attempts_sha256": sha256(arguments.attempts),
    }
    arguments.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
