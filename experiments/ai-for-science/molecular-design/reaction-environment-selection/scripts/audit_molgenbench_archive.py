#!/usr/bin/env python3
"""Audit MolGenBench archive bytes and fixture inventory without reading outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path, PurePosixPath

TARGET_FIXTURE = re.compile(
    r"(?:^|/)(?P<target>[A-Z0-9]+)/(?P=target)_(?P<kind>prep|pocket10|lig)\.(?:pdb|sdf)$"
)
OUTCOME_PARTS = {
    "results",
    "paper_results",
    "reference_active_molecules",
    "De_novo_Results",
    "Hit_to_Lead_Results",
}


def file_digests(path: Path) -> tuple[str, str, int]:
    sha256 = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            sha256.update(chunk)
            md5.update(chunk)
            size += len(chunk)
    return sha256.hexdigest(), md5.hexdigest(), size


def unsafe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return path.is_absolute() or ".." in path.parts


def audit(archive: Path, sources: Path) -> dict[str, object]:
    registry = json.loads(sources.read_text(encoding="utf-8"))
    expected = registry["molgenbench"]["dataset"]
    sha256, md5, size = file_digests(archive)
    errors: list[str] = []
    if size != expected["archive_size_bytes"]:
        errors.append(
            f"archive size differs: expected {expected['archive_size_bytes']}, got {size}"
        )
    if md5 != expected["published_md5"]:
        errors.append(f"archive MD5 differs: expected {expected['published_md5']}, got {md5}")

    fixtures: dict[str, set[str]] = {}
    outcome_members = 0
    unsafe_members: list[str] = []
    encrypted_members = 0
    compressed_bytes = 0
    uncompressed_bytes = 0
    with zipfile.ZipFile(archive) as handle:
        members = handle.infolist()
        for member in members:
            compressed_bytes += member.compress_size
            uncompressed_bytes += member.file_size
            if unsafe_member(member.filename):
                unsafe_members.append(member.filename)
            if member.flag_bits & 0x1:
                encrypted_members += 1
            parts = set(PurePosixPath(member.filename).parts)
            if parts & OUTCOME_PARTS:
                outcome_members += 1
            match = TARGET_FIXTURE.search(member.filename)
            if match:
                fixtures.setdefault(match.group("target"), set()).add(match.group("kind"))

    eligible_targets = sorted(
        target for target, kinds in fixtures.items() if kinds == {"prep", "pocket10", "lig"}
    )
    if unsafe_members:
        errors.append(f"archive contains {len(unsafe_members)} unsafe member paths")
    if encrypted_members:
        errors.append(f"archive contains {encrypted_members} encrypted members")
    if not eligible_targets:
        errors.append("archive contains no complete target fixture triplets")
    if errors:
        raise ValueError("; ".join(errors))

    target_digest = hashlib.sha256("\n".join(eligible_targets).encode()).hexdigest()
    return {
        "schema_version": "1.0",
        "study": registry["study"],
        "scope": "MolGenBench archive bytes, member metadata, and target fixture names",
        "archive": {
            "name": archive.name,
            "size_bytes": size,
            "sha256": sha256,
            "published_md5": md5,
            "members": len(members),
            "compressed_member_bytes": compressed_bytes,
            "uncompressed_member_bytes": uncompressed_bytes,
            "encrypted_members": encrypted_members,
            "unsafe_members": len(unsafe_members),
        },
        "target_fixtures": {
            "complete_targets": len(eligible_targets),
            "target_ids": eligible_targets,
            "target_ids_sha256": target_digest,
        },
        "sealed_boundary": {
            "outcome_members_present": outcome_members,
            "outcome_file_contents_read": False,
            "reference_active_contents_read": False,
            "published_model_results_read": False,
        },
        "qualification": "archive_metadata_pass_target_contents_open",
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--sources", type=Path, default=root / "SOURCES.json")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = audit(args.archive, args.sources)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
