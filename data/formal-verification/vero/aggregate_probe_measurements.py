#!/usr/bin/env python3
"""Validate Vero grade receipts and compute mode-specific policy measurements."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any


class AggregateError(ValueError):
    """Raised when probe receipts do not satisfy the frozen analysis contract."""


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AggregateError(f"expected an object in {path}")
    return value


def advantage_mass(successes: int, attempts: int) -> float:
    if attempts < 2 or not 0 <= successes <= attempts:
        raise AggregateError("invalid success count for leave-one-out advantage mass")
    return 2.0 * successes * (attempts - successes) / (attempts - 1)


def coordinates(groups: Iterable[dict[str, Any]]) -> dict[str, float | int]:
    measured = list(groups)
    if not measured:
        raise AggregateError("at least one specification group is required")
    total_mass = sum(record["advantage_mass"] for record in measured)
    total_tokens = sum(record["model_tokens"] for record in measured)
    if total_tokens <= 0:
        raise AggregateError("model-token denominator must be positive")
    squared_mass = sum(record["advantage_mass"] ** 2 for record in measured)
    coverage = 0.0 if squared_mass == 0 else total_mass**2 / (len(measured) * squared_mass)
    return {
        "rho_per_million_model_tokens": 1_000_000.0 * total_mass / total_tokens,
        "effective_coverage_H": coverage,
        "total_advantage_mass": total_mass,
        "model_tokens": total_tokens,
        "specification_groups": len(measured),
        "mixed_specification_groups": sum(record["advantage_mass"] > 0 for record in measured),
    }


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def cluster_sensitivity(
    groups_by_repository: dict[str, list[dict[str, Any]]], analysis: dict[str, Any]
) -> dict[str, Any]:
    repositories = sorted(groups_by_repository)
    if len(repositories) < 2:
        raise AggregateError("repository-cluster sensitivity requires at least two repositories")
    leave_one_out = {}
    for held_out in repositories:
        retained = [
            group
            for repository in repositories
            if repository != held_out
            for group in groups_by_repository[repository]
        ]
        leave_one_out[held_out] = coordinates(retained)

    contract = analysis["cluster_sensitivity"]
    rng = random.Random(contract["whole_repository_bootstrap_seed"])
    rho_samples: list[float] = []
    coverage_samples: list[float] = []
    for _ in range(contract["whole_repository_bootstrap_replicates"]):
        sampled = [rng.choice(repositories) for _ in repositories]
        groups = [group for repository in sampled for group in groups_by_repository[repository]]
        measurement = coordinates(groups)
        rho_samples.append(float(measurement["rho_per_million_model_tokens"]))
        coverage_samples.append(float(measurement["effective_coverage_H"]))
    alpha = (1 - contract["central_interval"]) / 2
    return {
        "leave_one_repository_out": leave_one_out,
        "whole_repository_bootstrap": {
            "replicates": contract["whole_repository_bootstrap_replicates"],
            "seed": contract["whole_repository_bootstrap_seed"],
            "central_interval": contract["central_interval"],
            "rho_interval": [quantile(rho_samples, alpha), quantile(rho_samples, 1 - alpha)],
            "H_interval": [
                quantile(coverage_samples, alpha),
                quantile(coverage_samples, 1 - alpha),
            ],
            "interpretation": contract["interpretation"],
        },
    }


def collect_receipts(grades_root: Path) -> dict[str, dict[str, Any]]:
    receipts: dict[str, dict[str, Any]] = {}
    for path in sorted(grades_root.rglob("grade-receipt.json")):
        receipt = read_object(path)
        attempt_id = receipt.get("attempt_id")
        if not isinstance(attempt_id, str) or not attempt_id:
            raise AggregateError(f"missing attempt identity in {path}")
        if attempt_id in receipts:
            raise AggregateError(f"duplicate grade receipt for {attempt_id}")
        receipts[attempt_id] = receipt
    return receipts


def validate_attempt(entry: dict[str, Any], receipt: dict[str, Any]) -> None:
    for field in ("attempt_id", "benchmark_id", "mode", "task_id"):
        if receipt.get(field) != entry[field]:
            raise AggregateError(f"{entry['attempt_id']} disagrees on {field}")
    if not receipt.get("infrastructure_valid"):
        raise AggregateError(f"{entry['attempt_id']} is infrastructure-invalid")
    if receipt.get("specifications_total") != entry["expected_specifications"]:
        raise AggregateError(f"{entry['attempt_id']} has an unexpected specification count")
    tokens = receipt.get("model_tokens")
    if not isinstance(tokens, int) or not 0 < tokens <= entry["maximum_model_tokens"]:
        raise AggregateError(f"{entry['attempt_id']} has invalid model-token usage")
    if not isinstance(receipt.get("peak_memory_bytes"), int) or receipt["peak_memory_bytes"] <= 0:
        raise AggregateError(f"{entry['attempt_id']} is missing peak memory")


def aggregate(queue: dict[str, Any], analysis: dict[str, Any], receipts: dict[str, Any]) -> dict:
    entries = queue["attempts"]
    expected = {entry["attempt_id"] for entry in entries}
    observed = set(receipts)
    if expected != observed:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        raise AggregateError(f"grade receipt set mismatch; missing={missing}, extra={extra}")
    attempts = analysis["attempts_per_group"]
    if any(entry["replicate"] > attempts for entry in entries):
        raise AggregateError("queue exceeds the frozen attempts per group")

    grouped: dict[tuple[str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for entry in entries:
        receipt = receipts[entry["attempt_id"]]
        validate_attempt(entry, receipt)
        grouped[(entry["mode"], entry["benchmark_id"])].append((entry, receipt))

    by_mode: dict[str, Any] = {}
    pooled_passes = 0
    pooled_trials = 0
    repositories_with_coverage: set[str] = set()
    total_mixed = 0
    for mode in sorted({entry["mode"] for entry in entries}):
        groups_by_repository: dict[str, list[dict[str, Any]]] = {}
        repository_summaries = {}
        for (record_mode, benchmark_id), records in sorted(grouped.items()):
            if record_mode != mode:
                continue
            if len(records) != attempts:
                raise AggregateError(f"{benchmark_id}:{mode} has {len(records)} attempts")
            specification_maps = []
            tokens_by_attempt = []
            for _, receipt in sorted(records, key=lambda pair: pair[0]["replicate"]):
                specification_map = {}
                for record in receipt["per_specification"]:
                    key = f"{record['module']}::{record['specification']}"
                    reward = record["strict_reward"]
                    if key in specification_map or reward not in (0, 1):
                        raise AggregateError(
                            f"invalid specification record in {receipt['attempt_id']}"
                        )
                    specification_map[key] = reward
                specification_maps.append(specification_map)
                tokens_by_attempt.append(receipt["model_tokens"])
            keys = set(specification_maps[0])
            if any(set(record) != keys for record in specification_maps[1:]):
                raise AggregateError(f"specification identities drifted in {benchmark_id}:{mode}")
            expected_specs = records[0][0]["expected_specifications"]
            if len(keys) != expected_specs:
                raise AggregateError(f"specification count drifted in {benchmark_id}:{mode}")
            repository_tokens = sum(tokens_by_attempt)
            repository_groups = []
            for key in sorted(keys):
                successes = sum(record[key] for record in specification_maps)
                repository_groups.append(
                    {
                        "repository": benchmark_id,
                        "specification": key,
                        "successes": successes,
                        "attempts": attempts,
                        "advantage_mass": advantage_mass(successes, attempts),
                        "model_tokens": repository_tokens / len(keys),
                    }
                )
            groups_by_repository[benchmark_id] = repository_groups
            passed = sum(group["successes"] for group in repository_groups)
            pooled_passes += passed
            pooled_trials += expected_specs * attempts
            if passed > 0:
                repositories_with_coverage.add(benchmark_id)
            measurement = coordinates(repository_groups)
            total_mixed += int(measurement["mixed_specification_groups"])
            repository_summaries[benchmark_id] = {
                **measurement,
                "strict_successes": passed,
                "strict_trials": expected_specs * attempts,
                "strict_success_rate": passed / (expected_specs * attempts),
            }
        mode_groups = [group for groups in groups_by_repository.values() for group in groups]
        by_mode[mode] = {
            "coordinates": coordinates(mode_groups),
            "repositories": repository_summaries,
            "cluster_sensitivity": cluster_sensitivity(groups_by_repository, analysis),
        }

    success_rate = pooled_passes / pooled_trials
    gates = analysis["admission_summary"]
    admission = {
        "repositories_with_nonzero_verified_coverage": len(repositories_with_coverage),
        "mixed_specification_groups": total_mixed,
        "pooled_strict_successes": pooled_passes,
        "pooled_strict_trials": pooled_trials,
        "pooled_strict_success_rate": success_rate,
    }
    admission["passes_measurement_support_gate"] = (
        len(repositories_with_coverage)
        >= gates["minimum_repositories_with_nonzero_verified_coverage"]
        and total_mixed >= gates["minimum_mixed_specification_groups"]
        and gates["minimum_pooled_strict_success"]
        <= success_rate
        <= gates["maximum_pooled_strict_success"]
    )
    return {
        "schema_version": "anarres.formal-verification-policy-measurement.v1",
        "queue_id": queue["queue_id"],
        "analysis_id": analysis["analysis_id"],
        "attempts": len(entries),
        "measurements_by_mode": by_mode,
        "admission_summary": admission,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--grades", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise AggregateError("--output must not exist")
    result = aggregate(
        read_object(args.queue),
        read_object(args.analysis),
        collect_receipts(args.grades),
    )
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote validated Vero policy measurements to {args.output}")


if __name__ == "__main__":
    main()
