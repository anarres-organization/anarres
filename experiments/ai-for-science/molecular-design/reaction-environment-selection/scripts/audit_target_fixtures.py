#!/usr/bin/env python3
"""Audit only the frozen MolGenBench target fixture files inside the archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import zipfile
from pathlib import Path

FIXTURE_PATTERN = re.compile(
    r"(?:^|/)(?P<target>[A-Z0-9]+)/(?P=target)_(?P<kind>prep|pocket10|lig)\.(?P<extension>pdb|sdf)$"
)
MAX_FIXTURE_BYTES = 64 * 1024 * 1024


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def audit_pdb(payload: bytes) -> dict[str, object]:
    text = payload.decode("utf-8")
    atoms = 0
    heteroatoms = 0
    residues: set[tuple[str, str, str]] = set()
    for line in text.splitlines():
        if not line.startswith(("ATOM  ", "HETATM")):
            continue
        if len(line) < 54:
            raise ValueError("PDB atom record is shorter than 54 columns")
        coordinates = [float(line[start:end]) for start, end in ((30, 38), (38, 46), (46, 54))]
        if not all(math.isfinite(value) for value in coordinates):
            raise ValueError("PDB contains non-finite coordinates")
        atoms += 1
        heteroatoms += line.startswith("HETATM")
        residues.add((line[21:22], line[22:26].strip(), line[17:20].strip()))
    if atoms == 0:
        raise ValueError("PDB contains no coordinate records")
    return {
        "coordinate_records": atoms,
        "heteroatom_records": heteroatoms,
        "unique_residue_keys": len(residues),
    }


def audit_sdf(payload: bytes) -> dict[str, object]:
    text = payload.decode("utf-8")
    records = [record for record in text.split("$$$$") if record.strip()]
    if not records:
        raise ValueError("SDF contains no molecule records")
    if any("M  END" not in record for record in records):
        raise ValueError("SDF molecule record lacks M  END")
    if not any(marker in text for marker in ("V2000", "V3000")):
        raise ValueError("SDF lacks a recognized molfile version")
    return {"molecule_records": len(records)}


def audit(
    archive: Path,
    archive_audit: dict[str, object],
    panel_freeze: dict[str, object],
) -> dict[str, object]:
    if panel_freeze.get("outcomes_inspected") is not False:
        raise ValueError("target panel must remain outcome blind")
    if panel_freeze.get("archive_sha256") != archive_audit["archive"]["sha256"]:
        raise ValueError("target panel and archive audit digests differ")
    if archive.stat().st_size != archive_audit["archive"]["size_bytes"]:
        raise ValueError("archive byte size differs from the qualified audit")
    targets = panel_freeze.get("target_ids")
    if not isinstance(targets, list) or len(targets) != panel_freeze.get("panel_size"):
        raise ValueError("target panel identities are malformed")

    by_target: dict[str, dict[str, zipfile.ZipInfo]] = {target: {} for target in targets}
    with zipfile.ZipFile(archive) as handle:
        for member in handle.infolist():
            match = FIXTURE_PATTERN.search(member.filename)
            if match is None or match.group("target") not in by_target:
                continue
            target = match.group("target")
            kind = match.group("kind")
            if kind in by_target[target]:
                raise ValueError(f"duplicate {kind} fixture for {target}")
            by_target[target][kind] = member

        target_results: list[dict[str, object]] = []
        for target in targets:
            fixtures = by_target[target]
            if set(fixtures) != {"prep", "pocket10", "lig"}:
                raise ValueError(f"incomplete fixture triplet for {target}")
            file_results: dict[str, object] = {}
            for kind in ("prep", "pocket10", "lig"):
                member = fixtures[kind]
                if member.flag_bits & 0x1:
                    raise ValueError(f"encrypted fixture for {target}: {kind}")
                if member.file_size <= 0 or member.file_size > MAX_FIXTURE_BYTES:
                    raise ValueError(f"invalid fixture size for {target}: {kind}")
                payload = handle.read(member)
                if len(payload) != member.file_size:
                    raise ValueError(f"short fixture read for {target}: {kind}")
                structural = audit_sdf(payload) if kind == "lig" else audit_pdb(payload)
                file_results[kind] = {
                    "archive_member": member.filename,
                    "size_bytes": len(payload),
                    "sha256": sha256_bytes(payload),
                    **structural,
                }
            target_results.append(
                {"target_id": target, "fixture_integrity": "pass", "files": file_results}
            )

    return {
        "schema_version": "1.0",
        "study": "prospective-reaction-environment-selection",
        "scope": "structural integrity of the frozen target fixture triplets",
        "archive_sha256": archive_audit["archive"]["sha256"],
        "target_panel_sha256": panel_freeze["target_ids_sha256"],
        "targets": target_results,
        "sealed_boundary": {
            "opened_member_kinds": [
                "target receptor PDB",
                "target pocket PDB",
                "reference ligand SDF",
            ],
            "opened_fixture_files": 3 * len(targets),
            "outcome_file_contents_read": False,
            "reference_active_contents_read": False,
            "published_model_results_read": False,
        },
        "qualification": "target_fixture_structure_pass_oracle_behavior_open",
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument(
        "--archive-audit", type=Path, default=root / "MOLGENBENCH_ARCHIVE_AUDIT.json"
    )
    parser.add_argument("--panel-freeze", type=Path, default=root / "TARGET_PANEL_FREEZE.json")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = audit(
        args.archive,
        json.loads(args.archive_audit.read_text(encoding="utf-8")),
        json.loads(args.panel_freeze.read_text(encoding="utf-8")),
    )
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
