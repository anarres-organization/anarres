#!/usr/bin/env python3
"""Materialize only frozen PBEsol structures while phonon outcomes remain sealed."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path, PurePosixPath


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def load_freeze(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    stored = payload.pop("panel_freeze_sha256")
    if canonical_digest(payload) != stored:
        raise ValueError("Panel freeze digest does not match its contents")
    payload["panel_freeze_sha256"] = stored
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pbesol-shard", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(f"Refusing to overwrite input root: {args.out}")
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    freeze = load_freeze(args.freeze)
    if contract["external_test_labels_inspected_at_freeze"] or freeze["external_labels_read"]:
        raise ValueError("PBEsol outcomes were not sealed at freeze")
    if sha256_path(args.pbesol_shard) != contract["source_shard_sha256"]:
        raise ValueError("PBEsol shard differs from the evaluation contract")
    if sha256_path(args.freeze) != contract["panel_freeze_file_sha256"]:
        raise ValueError("Panel freeze file differs from the evaluation contract")
    if freeze["panel_freeze_sha256"] != contract["panel_freeze_sha256"]:
        raise ValueError("Panel freeze canonical digest differs from the evaluation contract")

    from ase.io import read, write

    wanted = {row["poscar_member"]: row for row in freeze["records"]}
    if len(wanted) != contract["panels"]["pbesol"]["records"]:
        raise ValueError("Frozen panel size differs from the evaluation contract")
    materialized = []
    seen_members = set()
    with tarfile.open(args.pbesol_shard, "r") as archive:
        for member in archive:
            if member.name not in wanted:
                continue
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or not member.isfile():
                raise ValueError(f"Unsafe archive member: {member.name}")
            compressed = archive.extractfile(member).read()
            seen_members.add(member.name)
            frozen = wanted[member.name]
            if sha256_bytes(compressed) != frozen["poscar_gzip_sha256"]:
                raise ValueError(f"Frozen POSCAR digest differs: {member.name}")
            atoms = read(io.StringIO(gzip.decompress(compressed).decode("utf-8")), format="vasp")
            name = f"{frozen['material_id']}.cif"
            target = args.out / "pbesol" / "cifs" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            write(target, atoms, format="cif")
            contents = target.read_bytes()
            materialized.append(
                {
                    "panel": "pbesol",
                    "local_id": frozen["material_id"],
                    "cif_name": name,
                    "cif_sha256": sha256_bytes(contents),
                    "source_poscar_gzip_sha256": frozen["poscar_gzip_sha256"],
                    "reduced_composition": frozen["reduced_composition"],
                }
            )
    if len(materialized) != len(wanted):
        missing = sorted(set(wanted) - seen_members)
        raise ValueError(
            f"Incomplete structure materialization: {len(materialized)}; missing={missing[:3]}"
        )
    materialized.sort(key=lambda row: row["local_id"])
    manifest = {
        "schema_version": "1.0",
        "status": "complete_label_blind_pbesol_inputs",
        "evaluation_contract_file_sha256": sha256_path(args.contract),
        "panel_freeze_sha256": freeze["panel_freeze_sha256"],
        "source_shard_sha256": contract["source_shard_sha256"],
        "external_labels_read": False,
        "records": materialized,
    }
    manifest["input_manifest_sha256"] = canonical_digest(manifest)
    (args.out / "INPUT_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"records={len(materialized)}")
    print(f"input_manifest_sha256={manifest['input_manifest_sha256']}")


if __name__ == "__main__":
    main()
