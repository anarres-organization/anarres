#!/usr/bin/env python3
"""Freeze one MolGenBench target without post-training outcome access."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ALLOWED_ROOT_KEYS = {"schema_version", "source_archive_sha256", "targets"}
ALLOWED_TARGET_KEYS = {
    "target_id",
    "receptor_integrity",
    "pocket_integrity",
    "ligand_fixture_integrity",
    "oracle_input_integrity",
    "oracle_repeatability",
    "reference_control_validity",
    "starting_policy_validity",
    "starting_policy_headroom",
    "exclusion_reasons",
}
REQUIRED_PASS_FIELDS = {
    "receptor_integrity",
    "pocket_integrity",
    "ligand_fixture_integrity",
    "oracle_input_integrity",
    "oracle_repeatability",
    "reference_control_validity",
    "starting_policy_validity",
    "starting_policy_headroom",
}


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def selection_hash(target_id: str) -> str:
    return hashlib.sha256(f"reaction-environment-selection-v1|{target_id}".encode()).hexdigest()


def freeze(qualification: dict[str, object]) -> dict[str, object]:
    unexpected_root = set(qualification) - ALLOWED_ROOT_KEYS
    if unexpected_root:
        raise ValueError(f"unexpected qualification fields: {sorted(unexpected_root)}")
    targets = qualification.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("qualification must contain at least one target")

    identities: set[str] = set()
    eligible: list[str] = []
    excluded: dict[str, list[str]] = {}
    for target in targets:
        unexpected = set(target) - ALLOWED_TARGET_KEYS
        if unexpected:
            raise ValueError(
                f"unexpected fields for target {target.get('target_id')}: {sorted(unexpected)}"
            )
        target_id = target.get("target_id")
        if not isinstance(target_id, str) or not target_id:
            raise ValueError("every target requires a nonempty target_id")
        if target_id in identities:
            raise ValueError(f"duplicate target identity: {target_id}")
        identities.add(target_id)
        reasons = target.get("exclusion_reasons")
        if not isinstance(reasons, list) or any(
            not isinstance(reason, str) or not reason for reason in reasons
        ):
            raise ValueError(f"invalid exclusion_reasons for {target_id}")
        failed = sorted(field for field in REQUIRED_PASS_FIELDS if target.get(field) != "pass")
        if failed and not reasons:
            raise ValueError(f"{target_id} fails {failed} without an exclusion reason")
        if reasons:
            excluded[target_id] = reasons
        elif not failed:
            eligible.append(target_id)

    if not eligible:
        raise ValueError("no target passes the fixture and oracle-input gates")
    ranked = sorted(eligible, key=lambda target_id: (selection_hash(target_id), target_id))
    selected = ranked[0]
    return {
        "schema_version": "1.0",
        "study": "prospective-reaction-environment-selection",
        "status": "target_identity_frozen_reward_outcomes_unopened",
        "source_archive_sha256": qualification["source_archive_sha256"],
        "qualification_sha256": canonical_sha256(qualification),
        "selection_rule": "ascending SHA-256 of reaction-environment-selection-v1|target_id",
        "eligible_target_ids": sorted(eligible),
        "eligible_target_ids_sha256": canonical_sha256(sorted(eligible)),
        "selected_target_id": selected,
        "selected_target_hash": selection_hash(selected),
        "excluded_targets": excluded,
        "outcomes_inspected": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    qualification = json.loads(args.qualification.read_text(encoding="utf-8"))
    result = freeze(qualification)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
