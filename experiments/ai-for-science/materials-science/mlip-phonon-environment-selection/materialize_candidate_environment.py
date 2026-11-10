#!/usr/bin/env python3
"""Materialize one frozen MLIP candidate from the measured OMat24 pool."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def candidate_from_panel(panel_path: Path, candidate_id: str) -> dict:
    panel = json.loads(panel_path.read_text(encoding="utf-8"))
    matches = [
        candidate
        for candidate in panel.get("candidates", [])
        if candidate.get("candidate_id") == candidate_id
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one frozen candidate named {candidate_id!r}")
    return matches[0]


def membership_sha256(source_rows: list[object]) -> str:
    membership = "\n".join(row.data["sid"] for row in source_rows) + "\n"
    return hashlib.sha256(membership.encode()).hexdigest()


def materialize(panel_path: Path, source_path: Path, output_path: Path, candidate_id: str) -> dict:
    from ase_db_backends.aselmdb import LMDBDatabase

    if output_path.exists():
        raise FileExistsError(output_path)
    candidate = candidate_from_panel(panel_path, candidate_id)
    source = LMDBDatabase(str(source_path))
    indices = candidate["record_indices"]
    if len(indices) != len(set(indices)):
        raise ValueError("candidate contains duplicate record indices")

    source_rows = [source.get(index + 1) for index in indices]
    observed_membership = membership_sha256(source_rows)
    if observed_membership != candidate["membership_sha256"]:
        raise ValueError("candidate membership does not match the frozen panel")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    destination = LMDBDatabase(str(output_path))
    atoms = 0
    for ordinal, (record_index, source_row) in enumerate(zip(indices, source_rows, strict=True)):
        structure = source_row.toatoms()
        data = dict(source_row.data)
        data.update(
            {
                "anarres_candidate_id": candidate_id,
                "anarres_candidate_ordinal": ordinal,
                "anarres_measurement_record_index": record_index,
            }
        )
        destination.write(structure, data=data)
        atoms += len(structure)

    if atoms != candidate["atoms"]:
        raise ValueError(f"materialized {atoms} atoms; expected {candidate['atoms']}")
    return {
        "artifact": "anarres_mlip_materialized_candidate_v1",
        "candidate_id": candidate_id,
        "role": candidate.get("role", "unassigned"),
        "records": len(indices),
        "atoms": atoms,
        "neighbor_edges": candidate["neighbor_edges"],
        "membership_sha256": observed_membership,
        "source_pool": str(source_path),
        "output": str(output_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = materialize(args.panel, args.source, args.output, args.candidate_id)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
