#!/usr/bin/env python3
"""Audit conservative parent overlap between OMat24 and frozen phonon targets."""

from __future__ import annotations

import argparse
import bz2
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


FORMULA_TOKEN = re.compile(r"([A-Z][a-z]?)\s*([0-9]+(?:\.[0-9]+)?)")
PARENT_SPACE_GROUP = re.compile(r"(?:^|_)spg([0-9]+)(?:_|$)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def reduced_composition(counts: dict[str, int]) -> tuple[tuple[str, int], ...]:
    divisor = math.gcd(*counts.values())
    return tuple(sorted((element, count // divisor) for element, count in counts.items()))


def parse_reduced_formula(value: str) -> tuple[tuple[str, int], ...]:
    matches = FORMULA_TOKEN.findall(value)
    if not matches:
        raise ValueError(f"could not parse reduced composition: {value!r}")
    counts = {}
    for element, raw_count in matches:
        count = float(raw_count)
        if not count.is_integer():
            raise ValueError(f"non-integral reduced composition: {value!r}")
        counts[element] = counts.get(element, 0) + int(count)
    return reduced_composition(counts)


def parse_parent_space_group(parent_id: str) -> int:
    match = PARENT_SPACE_GROUP.search(parent_id)
    if match is None:
        raise ValueError(f"parent_id has no space-group field: {parent_id!r}")
    return int(match.group(1))


def target_descriptor(yaml_path: Path) -> tuple[tuple[tuple[str, int], ...], int]:
    with bz2.open(yaml_path, "rt", encoding="utf-8") as handle:
        in_primitive_cell = False
        in_primitive_points = False
        in_space_group = False
        counts = Counter()
        space_group = None
        for line in handle:
            if line == "primitive_cell:\n":
                in_primitive_cell = True
                continue
            if in_primitive_cell and line == "  points:\n":
                in_primitive_points = True
                continue
            if in_primitive_points and line == "  reciprocal_lattice:\n":
                in_primitive_points = False
                continue
            if in_primitive_points and line.startswith("    symbol: "):
                counts[line.split(":", maxsplit=1)[1].strip()] += 1
                continue
            if line == "space_group:\n":
                in_space_group = True
                continue
            if in_space_group and line.startswith("  number: "):
                space_group = int(line.split(":", maxsplit=1)[1])
                break
    if not counts or space_group is None:
        raise ValueError(f"missing primitive composition or space group in {yaml_path}")
    return reduced_composition(dict(counts)), space_group


def descriptor_text(descriptor: tuple[tuple[tuple[str, int], ...], int]) -> str:
    composition, space_group = descriptor
    formula = "".join(f"{element}{count}" for element, count in composition)
    return f"{formula}|spg{space_group}"


def parse_atomic_number_spec(value: str) -> set[int]:
    numbers = set()
    for part in value.split(","):
        bounds = part.strip().split("-", maxsplit=1)
        if len(bounds) == 1:
            numbers.add(int(bounds[0]))
        else:
            start, stop = map(int, bounds)
            numbers.update(range(start, stop + 1))
    return numbers


def audit_source(arguments: tuple) -> dict:
    (
        database_path,
        composition_targets,
        descriptor_targets,
        target_roles,
        supported_atomic_numbers,
    ) = arguments
    from ase.data import atomic_numbers
    from ase_db_backends.aselmdb import LMDBDatabase

    database = LMDBDatabase(str(database_path))
    source = database_path.parent.name
    source_composition_overlap = 0
    source_descriptor_overlap = 0
    source_parents = set()
    source_unsupported = 0
    source_ineligible = 0
    excluded_by_role = Counter()
    unsupported_elements = Counter()
    overlap_digest = hashlib.sha256()
    ineligible_digest = hashlib.sha256()

    for row_id in range(1, len(database) + 1):
        data = database.get(row_id).data
        composition = parse_reduced_formula(data["composition_reduced"])
        descriptor = (
            composition,
            parse_parent_space_group(data["parent_id"]),
        )
        composition_matches = composition_targets.get(composition)
        descriptor_matches = descriptor_targets.get(descriptor)
        if descriptor_matches:
            source_descriptor_overlap += 1
        if composition_matches:
            source_composition_overlap += 1
            source_parents.add(data["parent_id"])
            overlap_digest.update(f"{row_id}\t{data['sid']}\n".encode())
            for role in {target_roles[material_id] for material_id in composition_matches}:
                excluded_by_role[role] += 1
        unsupported = [
            element
            for element, _ in composition
            if atomic_numbers[element] not in supported_atomic_numbers
        ]
        if unsupported:
            source_unsupported += 1
            unsupported_elements.update(unsupported)
        if composition_matches or unsupported:
            source_ineligible += 1
            ineligible_digest.update(f"{row_id}\t{data['sid']}\n".encode())

    return {
        "source": source,
        "records": len(database),
        "target_composition_overlap_records": source_composition_overlap,
        "target_composition_space_group_overlap_records": source_descriptor_overlap,
        "target_overlap_parent_ids": source_parents,
        "target_overlap_record_sha256": overlap_digest.hexdigest(),
        "target_overlap_records_by_role": excluded_by_role,
        "unsupported_element_records": source_unsupported,
        "unsupported_element_counts": unsupported_elements,
        "ineligible_records": source_ineligible,
        "ineligible_record_sha256": ineligible_digest.hexdigest(),
    }


def audit(
    roles_path: Path,
    yaml_dir: Path,
    omat_train_root: Path,
    supported_atomic_numbers: set[int],
    workers: int,
) -> dict:
    roles = json.loads(roles_path.read_text(encoding="utf-8"))["roles"]
    target_roles = {
        material_id: role
        for role, material_ids in roles.items()
        for material_id in material_ids
    }
    target_descriptors = {}
    composition_targets = defaultdict(list)
    descriptor_targets = defaultdict(list)
    for material_id, role in target_roles.items():
        path = yaml_dir / f"{material_id}.yaml.bz2"
        descriptor = target_descriptor(path)
        target_descriptors[material_id] = {
            "role": role,
            "descriptor": descriptor_text(descriptor),
        }
        composition_targets[descriptor[0]].append(material_id)
        descriptor_targets[descriptor].append(material_id)

    source_results = {}
    total_records = 0
    excluded_records = 0
    excluded_parent_ids = set()
    excluded_by_role = Counter()
    unsupported_records = 0
    unsupported_elements = Counter()
    ineligible_records = 0
    overlap_manifest_digest = hashlib.sha256()
    ineligible_manifest_digest = hashlib.sha256()

    database_paths = sorted(omat_train_root.glob("*/train.aselmdb"))
    arguments = [
        (
            path,
            dict(composition_targets),
            dict(descriptor_targets),
            target_roles,
            supported_atomic_numbers,
        )
        for path in database_paths
    ]
    with ProcessPoolExecutor(max_workers=min(workers, len(arguments))) as executor:
        results = sorted(executor.map(audit_source, arguments), key=lambda row: row["source"])

    for row in results:
        source = row["source"]
        source_results[source] = {
            "records": row["records"],
            "target_composition_overlap_records": row[
                "target_composition_overlap_records"
            ],
            "target_composition_space_group_overlap_records": row[
                "target_composition_space_group_overlap_records"
            ],
            "target_overlap_parent_ids": len(row["target_overlap_parent_ids"]),
            "target_overlap_record_sha256": row["target_overlap_record_sha256"],
            "unsupported_element_records": row["unsupported_element_records"],
            "ineligible_records": row["ineligible_records"],
            "eligible_records": row["records"] - row["ineligible_records"],
            "ineligible_record_sha256": row["ineligible_record_sha256"],
        }
        total_records += row["records"]
        excluded_records += row["target_composition_overlap_records"]
        excluded_parent_ids.update(row["target_overlap_parent_ids"])
        excluded_by_role.update(row["target_overlap_records_by_role"])
        unsupported_records += row["unsupported_element_records"]
        unsupported_elements.update(row["unsupported_element_counts"])
        ineligible_records += row["ineligible_records"]
        overlap_manifest_digest.update(
            f"{source}\t{row['target_overlap_record_sha256']}\n".encode()
        )
        ineligible_manifest_digest.update(
            f"{source}\t{row['ineligible_record_sha256']}\n".encode()
        )
        print(
            f"{source}: {row['records']} records, {row['ineligible_records']} ineligible",
            flush=True,
        )

    return {
        "artifact": "anarres_omat24_target_overlap_audit_v1",
        "status": "complete",
        "rule": (
            "Exclude an OMat24 record when its reduced composition matches any frozen "
            "Alexandria target."
        ),
        "interpretation": (
            "This is a conservative chemistry-level leakage control. It excludes unrelated "
            "polymorphs with the same composition and does not assert structural identity."
        ),
        "inputs": {
            "roles_sha256": sha256(roles_path),
            "target_materials": len(target_roles),
            "unique_target_compositions": len(composition_targets),
            "unique_target_descriptors": len(descriptor_targets),
            "supported_atomic_numbers": sorted(supported_atomic_numbers),
        },
        "targets": target_descriptors,
        "construction_reservoir": {
            "records": total_records,
            "target_composition_overlap": {
                "records": excluded_records,
                "fraction": excluded_records / total_records,
                "parent_ids": len(excluded_parent_ids),
                "record_manifest_sha256": overlap_manifest_digest.hexdigest(),
                "records_by_target_role": dict(sorted(excluded_by_role.items())),
            },
            "target_composition_space_group_overlap_records": sum(
                row["target_composition_space_group_overlap_records"] for row in results
            ),
            "unsupported_element_records": unsupported_records,
            "unsupported_element_counts": dict(sorted(unsupported_elements.items())),
            "ineligible_records": ineligible_records,
            "eligible_records": total_records - ineligible_records,
            "ineligible_record_manifest_sha256": ineligible_manifest_digest.hexdigest(),
            "sources": source_results,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--roles", type=Path, required=True)
    parser.add_argument("--yaml-dir", type=Path, required=True)
    parser.add_argument("--omat-train-root", type=Path, required=True)
    parser.add_argument("--supported-atomic-numbers", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(
        args.roles,
        args.yaml_dir,
        args.omat_train_root,
        parse_atomic_number_spec(args.supported_atomic_numbers),
        args.workers,
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["construction_reservoir"], indent=2))


if __name__ == "__main__":
    main()
