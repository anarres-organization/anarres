#!/usr/bin/env python3
"""Construct the six frozen development banks from one starting-policy view."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def stable_hash(record_id: str) -> str:
    return hashlib.sha256(f"development-hash-v1|{record_id}".encode()).hexdigest()


def eligible_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_smiles: dict[str, dict[str, Any]] = {}
    for row in records:
        embedding = np.asarray(row["graph_embedding"], dtype=float)
        if row["reward_status"] != "ok" or not np.isfinite(embedding).all():
            continue
        smiles = str(row["canonical_smiles"])
        incumbent = by_smiles.get(smiles)
        if incumbent is None or row["record_id"] < incumbent["record_id"]:
            by_smiles[smiles] = row
    return sorted(by_smiles.values(), key=lambda row: row["record_id"])


def take_ranked(
    pool: list[dict[str, Any]],
    size: int,
    key: Callable[[dict[str, Any]], tuple[Any, ...]],
) -> list[dict[str, Any]]:
    if len(pool) < size:
        raise ValueError(f"eligible pool has {len(pool)} records, fewer than bank size {size}")
    return sorted(pool, key=key)[:size]


def reward_bank(pool: list[dict[str, Any]], size: int) -> list[dict[str, Any]]:
    ranked = sorted(pool, key=lambda row: (-float(row["target_reward"]), row["record_id"]))
    selected: list[dict[str, Any]] = []
    scaffold_counts: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()
    for row in ranked:
        scaffold = str(row["bemis_murcko_scaffold"])
        route = str(row["route_signature"])
        if scaffold_counts[scaffold] >= 8 or route_counts[route] >= 64:
            continue
        selected.append(row)
        scaffold_counts[scaffold] += 1
        route_counts[route] += 1
        if len(selected) == size:
            return selected
    selected_ids = {row["record_id"] for row in selected}
    for row in ranked:
        if row["record_id"] not in selected_ids:
            selected.append(row)
            if len(selected) == size:
                return selected
    raise ValueError("reward selector could not fill the requested bank")


def greedy_scaffold_bank(pool: list[dict[str, Any]], size: int) -> list[dict[str, Any]]:
    scaffold_frequency = Counter(str(row["bemis_murcko_scaffold"]) for row in pool)
    remaining = {row["record_id"]: row for row in pool}
    seen_scaffolds: set[str] = set()
    seen_rings: set[str] = set()
    selected = []
    while len(selected) < size:
        def priority(row: dict[str, Any]) -> tuple[Any, ...]:
            scaffold = str(row["bemis_murcko_scaffold"])
            rings = set(map(str, row["ring_systems"]))
            return (
                -(scaffold not in seen_scaffolds),
                -len(rings - seen_rings),
                scaffold_frequency[scaffold],
                row["record_id"],
            )

        chosen = min(remaining.values(), key=priority)
        selected.append(chosen)
        remaining.pop(chosen["record_id"])
        seen_scaffolds.add(str(chosen["bemis_murcko_scaffold"]))
        seen_rings.update(map(str, chosen["ring_systems"]))
    return selected


def greedy_route_bank(pool: list[dict[str, Any]], size: int) -> list[dict[str, Any]]:
    family_frequency = Counter(
        family for row in pool for family in set(map(str, row["reaction_families"]))
    )
    depth_frequency = Counter(int(row["reaction_depth"]) for row in pool)
    remaining = {row["record_id"]: row for row in pool}
    seen_families: set[str] = set()
    seen_depths: set[int] = set()
    selected = []
    while len(selected) < size:
        def gain(row: dict[str, Any]) -> float:
            families = set(map(str, row["reaction_families"])) - seen_families
            depth = int(row["reaction_depth"])
            family_gain = sum(1.0 / family_frequency[value] for value in families)
            depth_gain = 0.0 if depth in seen_depths else 1.0 / depth_frequency[depth]
            return family_gain + depth_gain

        chosen = min(remaining.values(), key=lambda row: (-gain(row), row["record_id"]))
        selected.append(chosen)
        remaining.pop(chosen["record_id"])
        seen_families.update(map(str, chosen["reaction_families"]))
        seen_depths.add(int(chosen["reaction_depth"]))
    return selected


def normalized_representation(pool: list[dict[str, Any]]) -> np.ndarray:
    values = np.asarray([row["graph_embedding"] for row in pool], dtype=float)
    centered = values - values.mean(axis=0, keepdims=True)
    _, singular, right = np.linalg.svd(centered, full_matrices=False)
    tolerance = np.finfo(float).eps * max(centered.shape) * singular[0]
    rank = int(np.sum(singular > tolerance))
    components = min(32, rank)
    if components == 0:
        raise ValueError("graph representation has zero empirical rank")
    projected = centered @ right[:components].T
    projected /= singular[:components]
    norms = np.linalg.norm(projected, axis=1, keepdims=True)
    return np.divide(projected, norms, out=np.zeros_like(projected), where=norms > 0)


def graph_bank(pool: list[dict[str, Any]], size: int) -> list[dict[str, Any]]:
    values = normalized_representation(pool)
    centroid = values.mean(axis=0)
    start_distances = np.linalg.norm(values - centroid, axis=1)
    start = min(
        range(len(pool)),
        key=lambda index: (start_distances[index], pool[index]["record_id"]),
    )
    selected_indices = [start]
    minimum_distances = np.linalg.norm(values - values[start], axis=1)
    while len(selected_indices) < size:
        selected_set = set(selected_indices)
        chosen = min(
            (index for index in range(len(pool)) if index not in selected_set),
            key=lambda index: (-minimum_distances[index], pool[index]["record_id"]),
        )
        selected_indices.append(chosen)
        minimum_distances = np.minimum(
            minimum_distances, np.linalg.norm(values - values[chosen], axis=1)
        )
    return [pool[index] for index in selected_indices]


def construct(records: list[dict[str, Any]], size: int) -> dict[str, list[dict[str, Any]]]:
    pool = eligible_records(records)
    return {
        "hash_uniform": take_ranked(pool, size, lambda row: (stable_hash(row["record_id"]),)),
        "reward_signal": reward_bank(pool, size),
        "validity_cost": take_ranked(
            pool,
            size,
            lambda row: (
                int(row["generated_action_count"]),
                float(row["oracle_elapsed_seconds"]),
                row["record_id"],
            ),
        ),
        "scaffold_coverage": greedy_scaffold_bank(pool, size),
        "route_coverage": greedy_route_bank(pool, size),
        "graph_embedding_coverage": graph_bank(pool, size),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--bank-size", type=int, default=512)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    banks = construct(read_jsonl(args.records), args.bank_size)
    result = {
        "schema_version": "1.0",
        "source_records": str(args.records.name),
        "bank_size": args.bank_size,
        "banks": {
            name: [row["record_id"] for row in members] for name, members in banks.items()
        },
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({name: len(members) for name, members in banks.items()}, sort_keys=True))


if __name__ == "__main__":
    main()
