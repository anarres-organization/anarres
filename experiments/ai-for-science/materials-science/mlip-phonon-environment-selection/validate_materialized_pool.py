#!/usr/bin/env python3
"""Validate labels and provenance in a materialized ASE-LMDB pool."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(database_path: Path, expected_records_per_family: int | None) -> dict:
    from ase_db_backends.aselmdb import LMDBDatabase

    database = LMDBDatabase(str(database_path))
    families = Counter()
    identities = set()
    ordinals = []
    atoms = 0
    maximum_atoms = 0
    for row_id in range(1, len(database) + 1):
        row = database.get(row_id)
        data = row.data
        structure = row.toatoms()
        family = data["anarres_source_family"]
        identity = (data["anarres_source"], data["anarres_source_row_id"], data["sid"])
        if identity in identities:
            raise ValueError(f"duplicate source identity: {identity}")
        identities.add(identity)
        ordinals.append(data["anarres_manifest_ordinal"])
        families[family] += 1
        atoms += len(structure)
        maximum_atoms = max(maximum_atoms, len(structure))
        labels = {
            "energy": structure.get_potential_energy(),
            "force": structure.get_forces(),
            "stress": structure.get_stress(voigt=False),
        }
        for name, value in labels.items():
            if not np.isfinite(np.asarray(value)).all():
                raise ValueError(f"record {row_id} has non-finite {name}")
        if np.asarray(labels["force"]).shape != (len(structure), 3):
            raise ValueError(f"record {row_id} has an invalid force shape")
        if np.asarray(labels["stress"]).shape != (3, 3):
            raise ValueError(f"record {row_id} has an invalid stress shape")

    if sorted(ordinals) != list(range(len(database))):
        raise ValueError("manifest ordinals are not contiguous")
    if expected_records_per_family is not None and any(
        count != expected_records_per_family for count in families.values()
    ):
        raise ValueError("source-family counts do not match the expected count")
    return {
        "artifact": "anarres_mlip_materialized_pool_validation_v1",
        "database_sha256": sha256(database_path),
        "records": len(database),
        "atoms": atoms,
        "maximum_atoms_per_record": maximum_atoms,
        "source_families": dict(sorted(families.items())),
        "labels": {"energy": "finite", "force": "finite", "stress": "finite"},
        "provenance": {"unique_source_identities": True, "contiguous_ordinals": True},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--expected-records-per-family", type=int)
    args = parser.parse_args()
    result = validate(args.database, args.expected_records_per_family)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
