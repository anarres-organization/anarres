#!/usr/bin/env python3
"""Materialize an exact ASE-LMDB subset from a measurement-pool manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def selected_rows(manifest: Path, records_per_family: int | None) -> list[dict]:
    rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
    if records_per_family is None:
        return rows
    if records_per_family <= 0:
        raise ValueError("records_per_family must be positive")
    counts = Counter()
    selected = []
    for row in rows:
        family = row["source_family"]
        if counts[family] >= records_per_family:
            continue
        counts[family] += 1
        selected.append(row)
    expected = {row["source_family"] for row in rows}
    if set(counts) != expected or any(counts[family] != records_per_family for family in expected):
        raise RuntimeError("manifest does not contain the requested records per source family")
    return selected


def materialize(
    manifest: Path,
    source_root: Path,
    output: Path,
    records_per_family: int | None,
) -> dict:
    from ase_db_backends.aselmdb import LMDBDatabase

    if output.exists():
        raise FileExistsError(output)
    rows = selected_rows(manifest, records_per_family)
    output.parent.mkdir(parents=True, exist_ok=True)
    destination = LMDBDatabase(str(output))
    sources = {}
    digest = hashlib.sha256()
    atom_count = 0
    for ordinal, row in enumerate(rows):
        source = row["source"]
        if source not in sources:
            sources[source] = LMDBDatabase(str(source_root / source / "train.aselmdb"))
        source_row = sources[source].get(row["row_id"])
        if source_row.data["sid"] != row["sid"]:
            raise ValueError(f"source identity mismatch for {row['sid']}")
        atoms = source_row.toatoms()
        data = dict(source_row.data)
        data.update(
            {
                "anarres_manifest_ordinal": ordinal,
                "anarres_source": source,
                "anarres_source_family": row["source_family"],
                "anarres_source_row_id": row["row_id"],
                "anarres_hash_score": row["hash_score"],
            }
        )
        destination.write(atoms, data=data)
        atom_count += len(atoms)
        digest.update(f"{ordinal}\t{source}\t{row['row_id']}\t{row['sid']}\n".encode())

    return {
        "artifact": "anarres_mlip_materialized_pool_v1",
        "records": len(rows),
        "atoms": atom_count,
        "source_families": dict(sorted(Counter(row["source_family"] for row in rows).items())),
        "manifest_selection_sha256": digest.hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--records-per-family", type=int)
    args = parser.parse_args()
    summary = materialize(
        args.manifest,
        args.source_root,
        args.output,
        args.records_per_family,
    )
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
