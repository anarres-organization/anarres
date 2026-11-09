#!/usr/bin/env python3
"""Construct an equal-atom, outcome-blind draft MLIP candidate bank."""

from __future__ import annotations

import argparse
import bz2
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml

SELECTION_RULES = (
    "hash_uniform",
    "low_signal",
    "high_signal",
    "coverage",
    "target_affinity",
    "signal_coverage_affinity",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def elements_from_formula(formula: str) -> frozenset[str]:
    return frozenset(re.findall(r"[A-Z][a-z]?", formula))


def target_element_sets(
    target_roles_path: Path, target_yaml_dir: Path, role: str
) -> list[frozenset[str]]:
    roles = json.loads(target_roles_path.read_text(encoding="utf-8"))
    sets = []
    for material_id in roles["roles"][role]:
        with bz2.open(target_yaml_dir / f"{material_id}.yaml.bz2", "rt") as handle:
            payload = yaml.safe_load(handle)
        sets.append(frozenset(point["symbol"] for point in payload["unit_cell"]["points"]))
    return sets


def load_records(manifest_path: Path, measurement_paths: list[Path]) -> list[dict]:
    manifest = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()]
    measurements = []
    for path in measurement_paths:
        measurements.extend(
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        )
    measurements.sort(key=lambda row: row["record_index"])
    if len(manifest) != len(measurements):
        raise ValueError(
            f"manifest has {len(manifest)} rows; measurements have {len(measurements)}"
        )
    if [row["record_index"] for row in measurements] != list(range(len(manifest))):
        raise ValueError("measurement record indices are not contiguous")
    records = []
    for metadata, measurement in zip(manifest, measurements, strict=True):
        elements = elements_from_formula(metadata["composition_reduced"])
        records.append(
            metadata
            | measurement
            | {
                "elements": sorted(elements),
                "chemical_system": "-".join(sorted(elements)),
                "signal_density": 20.0 * measurement["force_l2_mean"]
                + 5.0 * measurement["stress_mae"] / measurement["natoms"],
                "signal_mass": 20.0 * measurement["force_l2_mean"] * measurement["natoms"]
                + 5.0 * measurement["stress_mae"],
            },
        )
    return records


def percentile_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    ranks = [0.0] * len(values)
    denominator = max(1, len(values) - 1)
    for rank, index in enumerate(order):
        ranks[index] = rank / denominator
    return ranks


def score_family(records: list[dict], targets: list[frozenset[str]]) -> None:
    systems = Counter(row["chemical_system"] for row in records)
    prototypes = Counter(row["parent_prototype_label"] for row in records)
    for row in records:
        elements = frozenset(row["elements"])
        row["coverage_score"] = (
            0.5 / systems[row["chemical_system"]] + 0.5 / prototypes[row["parent_prototype_label"]]
        )
        row["target_affinity"] = max(
            len(elements & target) / len(elements | target) for target in targets
        )
    signal_rank = percentile_ranks([row["signal_density"] for row in records])
    coverage_rank = percentile_ranks([row["coverage_score"] for row in records])
    affinity_rank = percentile_ranks([row["target_affinity"] for row in records])
    for index, row in enumerate(records):
        row["hybrid_score"] = (
            signal_rank[index] + coverage_rank[index] + affinity_rank[index]
        ) / 3.0


def ranking_key(rule: str, row: dict) -> tuple:
    if rule == "hash_uniform":
        return (row["hash_score"],)
    directions = {
        "low_signal": ("signal_density", False),
        "high_signal": ("signal_density", True),
        "coverage": ("coverage_score", True),
        "target_affinity": ("target_affinity", True),
        "signal_coverage_affinity": ("hybrid_score", True),
    }
    field, descending = directions[rule]
    value = -row[field] if descending else row[field]
    return (value, row["hash_score"])


def select_equal_atoms(records: list[dict], rule: str, atom_budget: int) -> list[dict]:
    ranked = sorted(records, key=lambda row: ranking_key(rule, row))
    ranked_unique = []
    observed_parents = set()
    for row in ranked:
        if row["parent_id"] in observed_parents:
            continue
        observed_parents.add(row["parent_id"])
        ranked_unique.append(row)

    repair_window = min(2_000, atom_budget // 10)
    prefix_limit = atom_budget - repair_window
    selected = []
    deferred = []
    atoms = 0
    for row in ranked_unique:
        if atoms + row["natoms"] <= prefix_limit:
            selected.append(row)
            atoms += row["natoms"]
        else:
            deferred.append(row)

    target = atom_budget - atoms
    reachable: dict[int, tuple[dict, ...]] = {0: ()}
    for row in deferred:
        for subtotal, subset in sorted(reachable.items(), reverse=True):
            updated = subtotal + row["natoms"]
            if updated > target or updated in reachable:
                continue
            reachable[updated] = subset + (row,)
        if target in reachable:
            result = selected + list(reachable[target])
            if sum(row["natoms"] for row in result) != atom_budget:
                raise AssertionError("exact-budget construction produced the wrong atom count")
            return result
    raise RuntimeError(
        f"{rule} could not fill the exact {atom_budget}-atom budget from unique parents"
    )


def normalized_effective_coverage(masses: list[float]) -> float:
    total = sum(masses)
    if total <= 0:
        return 0.0
    return total**2 / (len(masses) * sum(value**2 for value in masses))


def entropy(values: list[str]) -> float:
    counts = Counter(values)
    total = len(values)
    if len(counts) <= 1:
        return 0.0
    raw = -sum((count / total) * math.log(count / total) for count in counts.values())
    return raw / math.log(len(counts))


def summarize_candidate(candidate_id: str, selected: list[dict]) -> dict:
    membership = "\n".join(row["sid"] for row in selected) + "\n"
    atoms = sum(row["natoms"] for row in selected)
    edges = sum(row["neighbor_edges"] for row in selected)
    masses = [row["signal_mass"] for row in selected]
    return {
        "candidate_id": candidate_id,
        "records": len(selected),
        "atoms": atoms,
        "neighbor_edges": edges,
        "neighbor_edges_per_atom": edges / atoms,
        "parents": len({row["parent_id"] for row in selected}),
        "chemical_systems": len({row["chemical_system"] for row in selected}),
        "parent_prototypes": len({row["parent_prototype_label"] for row in selected}),
        "signal_density_per_atom": sum(masses) / atoms,
        "effective_signal_coverage": normalized_effective_coverage(masses),
        "chemical_system_entropy": entropy([row["chemical_system"] for row in selected]),
        "mean_target_affinity": sum(row["target_affinity"] for row in selected) / len(selected),
        "membership_sha256": hashlib.sha256(membership.encode()).hexdigest(),
        "record_indices": [row["record_index"] for row in selected],
    }


def construct(
    manifest_path: Path,
    measurement_paths: list[Path],
    target_roles_path: Path,
    target_yaml_dir: Path,
    atom_budget: int,
) -> dict:
    targets = target_element_sets(target_roles_path, target_yaml_dir, "checkpoint_qualification")
    records = load_records(manifest_path, measurement_paths)
    families = defaultdict(list)
    for row in records:
        families[row["source_family"]].append(row)

    candidates = []
    for family in sorted(families):
        family_records = families[family]
        score_family(family_records, targets)
        for rule in SELECTION_RULES:
            selected = select_equal_atoms(family_records, rule, atom_budget)
            candidate_id = f"{family}__{rule}"
            candidates.append(summarize_candidate(candidate_id, selected))

    return {
        "artifact": "anarres_mlip_candidate_bank_draft_v1",
        "status": "measurement_only_draft__no_candidate_outcomes_observed",
        "inputs": {
            "manifest_sha256": sha256(manifest_path),
            "measurement_sha256": {path.name: sha256(path) for path in measurement_paths},
            "target_roles_sha256": sha256(target_roles_path),
            "target_role_used_for_affinity": "checkpoint_qualification",
        },
        "construction": {
            "atom_budget_per_candidate": atom_budget,
            "maximum_records_per_parent": 1,
            "source_families": sorted(families),
            "selection_rules": list(SELECTION_RULES),
            "uses_candidate_training_outcomes": False,
            "uses_development_or_prospective_target_outcomes": False,
        },
        "candidates": candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--measurements", type=Path, nargs="+", required=True)
    parser.add_argument("--target-roles", type=Path, required=True)
    parser.add_argument("--target-yaml-dir", type=Path, required=True)
    parser.add_argument("--atom-budget", type=int, default=50_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = construct(
        args.manifest,
        sorted(args.measurements),
        args.target_roles,
        args.target_yaml_dir,
        args.atom_budget,
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "artifact": result["artifact"],
                "status": result["status"],
                "candidates": len(result["candidates"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
