#!/usr/bin/env python3
"""Freeze an outcome-blind MolGenBench target qualification panel."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def panel_hash(target_id: str) -> str:
    return hashlib.sha256(f"reaction-target-panel-v1|{target_id}".encode()).hexdigest()


def freeze(archive_audit: dict[str, object], panel_size: int) -> dict[str, object]:
    if panel_size <= 0:
        raise ValueError("panel_size must be positive")
    boundary = archive_audit.get("sealed_boundary")
    if not isinstance(boundary, dict):
        raise ValueError("archive audit lacks a sealed boundary")
    forbidden = (
        "outcome_file_contents_read",
        "reference_active_contents_read",
        "published_model_results_read",
    )
    if any(boundary.get(field) is not False for field in forbidden):
        raise ValueError("archive outcomes must remain unopened")
    fixtures = archive_audit.get("target_fixtures")
    if not isinstance(fixtures, dict):
        raise ValueError("archive audit lacks target fixtures")
    targets = fixtures.get("target_ids")
    if not isinstance(targets, list) or any(
        not isinstance(target, str) or not target for target in targets
    ):
        raise ValueError("archive audit contains invalid target identities")
    if len(targets) != len(set(targets)):
        raise ValueError("archive audit contains duplicate target identities")
    if panel_size > len(targets):
        raise ValueError("panel_size exceeds the complete target inventory")
    ranked = sorted(targets, key=lambda target: (panel_hash(target), target))
    panel = ranked[:panel_size]
    archive = archive_audit.get("archive")
    if not isinstance(archive, dict) or not archive.get("sha256"):
        raise ValueError("archive audit lacks an archive SHA-256 digest")
    return {
        "schema_version": "1.0",
        "study": "prospective-reaction-environment-selection",
        "status": "target_qualification_panel_frozen_outcomes_unopened",
        "archive_sha256": archive["sha256"],
        "archive_audit_sha256": canonical_sha256(archive_audit),
        "selection_rule": (
            "first panel_size identities by SHA-256 of reaction-target-panel-v1|target_id"
        ),
        "source_target_count": len(targets),
        "panel_size": panel_size,
        "target_ids": panel,
        "target_ids_sha256": canonical_sha256(panel),
        "outcomes_inspected": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-audit", type=Path, required=True)
    parser.add_argument("--panel-size", type=int, default=8)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    archive_audit = json.loads(args.archive_audit.read_text(encoding="utf-8"))
    result = freeze(archive_audit, args.panel_size)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
