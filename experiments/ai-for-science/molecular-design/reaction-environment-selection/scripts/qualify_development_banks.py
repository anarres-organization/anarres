#!/usr/bin/env python3
"""Construct development banks and apply the frozen two-view confirmation gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from construct_development_banks import construct, eligible_records, normalized_representation


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def average_ranks(values: list[float]) -> np.ndarray:
    order = np.argsort(np.asarray(values), kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1) + 1.0
        start = end
    return ranks


def spearman(first: list[float], second: list[float]) -> tuple[float, str]:
    first_array = np.asarray(first, dtype=float)
    second_array = np.asarray(second, dtype=float)
    first_constant = bool(np.all(first_array == first_array[0]))
    second_constant = bool(np.all(second_array == second_array[0]))
    if first_constant and second_constant:
        return 1.0, "constant_in_both_views"
    if first_constant or second_constant:
        return 0.0, "constant_in_one_view"
    result = float(np.corrcoef(average_ranks(first), average_ranks(second))[0, 1])
    return result, "finite"


def summarize_bank(
    members: list[dict[str, Any]],
    pool: list[dict[str, Any]],
    pool_representation: np.ndarray,
) -> dict[str, float]:
    bank_ids = {row["record_id"] for row in members}
    indices = [index for index, row in enumerate(pool) if row["record_id"] in bank_ids]
    selected_values = pool_representation[indices]
    distances = np.linalg.norm(selected_values[:, None, :] - selected_values[None, :, :], axis=2)
    np.fill_diagonal(distances, np.inf)
    nearest = np.min(distances, axis=1)
    scaffolds = {str(row["bemis_murcko_scaffold"]) for row in members}
    ring_systems = {str(value) for row in members for value in row["ring_systems"]}
    routes = {str(row["route_signature"]) for row in members}
    families = {str(value) for row in members for value in row["reaction_families"]}
    return {
        "mean_target_reward": float(np.mean([row["target_reward"] for row in members])),
        "mean_generated_action_count": float(
            np.mean([row["generated_action_count"] for row in members])
        ),
        "mean_oracle_seconds": float(np.mean([row["oracle_elapsed_seconds"] for row in members])),
        "unique_scaffold_fraction": len(scaffolds) / len(members),
        "unique_ring_systems_per_record": len(ring_systems) / len(members),
        "unique_route_fraction": len(routes) / len(members),
        "unique_reaction_families": float(len(families)),
        "embedding_mean_nearest_neighbor_distance": float(np.mean(nearest)),
    }


def jaccard(first: set[str], second: set[str]) -> float:
    union = first | second
    return len(first & second) / len(union) if union else 1.0


def qualify(
    records_by_view: list[list[dict[str, Any]]],
    contract: dict[str, Any],
    bank_contract: dict[str, Any],
) -> dict[str, Any]:
    if len(records_by_view) != 2:
        raise ValueError("the bank confirmation contract requires exactly two views")
    size = int(bank_contract["bank_size"])
    names = list(bank_contract["development_bank_order"])
    pools = [eligible_records(records) for records in records_by_view]
    banks = [construct(records, size) for records in records_by_view]
    representations = [normalized_representation(pool) for pool in pools]
    summaries = [
        {name: summarize_bank(view_banks[name], pool, representation) for name in names}
        for view_banks, pool, representation in zip(banks, pools, representations, strict=True)
    ]
    minimum = float(bank_contract["confirmation_rule"]["minimum_correlation"])
    correlations = {}
    checks = {}
    for coordinate in bank_contract["summary_coordinates"]:
        value, status = spearman(
            [summaries[0][name][coordinate] for name in names],
            [summaries[1][name][coordinate] for name in names],
        )
        correlations[coordinate] = {"spearman": value, "status": status}
        checks[coordinate] = value >= minimum
    construction_sets = {name: {row["record_id"] for row in banks[0][name]} for name in names}
    overlaps = {
        first: {
            second: jaccard(construction_sets[first], construction_sets[second]) for second in names
        }
        for first in names
    }
    return {
        "schema_version": "1.0",
        "study": contract["study"],
        "scope": "development-bank construction and two-view confirmation",
        "qualification": "pass" if all(checks.values()) else "fail",
        "view_seeds": contract["sampling"]["seeds"],
        "eligible_unique_products": [len(pool) for pool in pools],
        "bank_size": size,
        "construction_memberships": {
            name: [row["record_id"] for row in banks[0][name]] for name in names
        },
        "confirmation_reconstruction_memberships": {
            name: [row["record_id"] for row in banks[1][name]] for name in names
        },
        "summaries": summaries,
        "rank_correlations": correlations,
        "confirmation_checks": checks,
        "construction_membership_jaccard": overlaps,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--bank-contract", type=Path, required=True)
    parser.add_argument("--records", type=Path, action="append", required=True)
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(args.records) != 2 or len(args.manifest) != 2:
        raise ValueError("supply exactly two records files and two manifests")
    manifests = [read_json(path) for path in args.manifest]
    contract = read_json(args.contract)
    if [manifest["view_seed"] for manifest in manifests] != contract["sampling"]["seeds"]:
        raise ValueError("view seeds do not match the measurement contract")
    for records_path, manifest in zip(args.records, manifests, strict=True):
        if file_sha256(records_path) != manifest["output_sha256"]:
            raise ValueError(f"records digest mismatch: {records_path}")
    result = qualify(
        [read_jsonl(path) for path in args.records],
        contract,
        read_json(args.bank_contract),
    )
    result["input_sha256"] = {
        path.name: file_sha256(path) for path in [*args.records, *args.manifest]
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"qualification": result["qualification"]}))


if __name__ == "__main__":
    main()
