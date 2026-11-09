#!/usr/bin/env python3
"""Extract only external-panel CIFs before held-out labels are opened."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from zipfile import ZipFile


def sha256_bytes(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_digest(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    if contract["external_test_labels_inspected_at_freeze"]:
        raise ValueError("Evaluation contract was not frozen behind the sealed boundary")
    if sha256(args.archive) != contract["source_archive_sha256"]:
        raise ValueError("Source archive differs from the frozen evaluation contract")
    if args.out.exists():
        raise FileExistsError(f"Refusing to overwrite external input root: {args.out}")

    rows = []
    with ZipFile(args.archive) as archive:
        names = archive.namelist()
        for panel, spec in contract["panels"].items():
            prefix = spec["archive_prefix"] + "/cifs/"
            members = sorted(
                name for name in names if name.startswith(prefix) and name.endswith(".cif")
            )
            if len(members) != spec["records"]:
                raise ValueError(
                    f"Expected {spec['records']} label-blind CIFs for {panel}, found {len(members)}"
                )
            for member_name in members:
                member = PurePosixPath(member_name)
                if member.is_absolute() or ".." in member.parts or len(member.parts) < 3:
                    raise ValueError(f"Unsafe archive member: {member_name}")
                contents = archive.read(member_name)
                local_name = member.name
                target = args.out / panel / "cifs" / local_name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(contents)
                rows.append(
                    {
                        "panel": panel,
                        "local_id": Path(local_name).stem,
                        "cif_name": local_name,
                        "cif_sha256": sha256_bytes(contents),
                    }
                )

    identities = [(row["panel"], row["local_id"]) for row in rows]
    if len(identities) != len(set(identities)):
        raise ValueError("External CIF identities are not unique within panel")
    manifest = {
        "schema_version": "1.0",
        "status": "label_blind_external_cifs_materialized",
        "evaluation_contract_sha256": sha256(args.contract),
        "source_archive_sha256": contract["source_archive_sha256"],
        "external_labels_read": False,
        "records": rows,
    }
    manifest["input_manifest_sha256"] = canonical_digest(manifest)
    (args.out / "INPUT_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"records={len(rows)}")
    print(f"input_manifest_sha256={manifest['input_manifest_sha256']}")


if __name__ == "__main__":
    main()
