#!/usr/bin/env python3
"""Materialize the frozen phonon candidate launch matrix without training."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_freeze(freeze: dict[str, Any], protocol: dict[str, Any]) -> None:
    stored_digest = freeze.get("freeze_sha256")
    digest_payload = dict(freeze)
    digest_payload.pop("freeze_sha256", None)
    if stored_digest != canonical_digest(digest_payload):
        raise ValueError("Freeze digest does not match its contents")
    if freeze.get("protocol_sha256") != canonical_digest(protocol):
        raise ValueError("Freeze is not bound to the supplied protocol")
    if freeze.get("status") != "candidates_frozen_outcomes_sealed":
        raise ValueError("Candidate freeze is not launchable")
    if freeze.get("external_test_labels_inspected"):
        raise ValueError("External labels must remain sealed at launch materialization")
    if freeze.get("candidate_training_outcomes_exist"):
        raise ValueError("Candidate outcomes already exist")
    if not freeze["repeatability"]["passes"]:
        raise ValueError("Repeatability gate did not pass")


def candidate_matrix(freeze: dict[str, Any], protocol: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = protocol["candidate_construction"]["candidate_names"]
    budgets = protocol["candidate_construction"]["budgets_structures"]
    seeds = protocol["training"]["seeds"]
    rows = []
    for candidate in candidates:
        for budget in budgets:
            frozen = freeze["candidates"][candidate][str(budget)]["record_ids"]
            if len(frozen) != budget or len(set(frozen)) != budget:
                raise ValueError(f"Invalid frozen membership for {candidate} at {budget}")
            rows.extend(
                {
                    "run_id": f"phonon-{candidate.replace('_', '-')}-n{budget}-s{seed}",
                    "candidate": candidate,
                    "budget_structures": budget,
                    "seed": seed,
                    "split_file": f"splits/{candidate}_n{budget}.json",
                    "expected_train_records": budget,
                    "expected_validation_records": 411,
                    "status": "planned",
                }
                for seed in seeds
            )
    expected = len(candidates) * len(budgets) * len(seeds)
    if len(rows) != expected or len({row["run_id"] for row in rows}) != expected:
        raise ValueError("Launch matrix is incomplete or contains duplicate run IDs")
    return rows


def materialize(
    *,
    freeze_path: Path,
    protocol_path: Path,
    manifest_path: Path,
    released_split_path: Path,
    out_dir: Path,
) -> dict[str, Any]:
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    validate_freeze(freeze, protocol)
    if sha256(manifest_path) != protocol["source"]["training_manifest_sha256"]:
        raise ValueError("Training manifest digest differs from the frozen protocol")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    eligible = [row for row in manifest if row["role"] == "gradient_train"]
    by_record_id = {row["record_id"]: row["cif_path"] for row in eligible}
    if len(by_record_id) != protocol["source"]["gradient_training_records"]:
        raise ValueError("Eligible source identities are incomplete or duplicated")

    released_split = json.loads(released_split_path.read_text(encoding="utf-8"))
    validation = released_split["id_val"]
    internal_test = released_split["id_test"]
    if len(validation) != 411 or validation != internal_test:
        raise ValueError("Released checkpoint validation contract changed")

    split_dir = out_dir / "splits"
    split_dir.mkdir(parents=True, exist_ok=True)
    split_hashes: dict[str, str] = {}
    candidates = protocol["candidate_construction"]["candidate_names"]
    budgets = protocol["candidate_construction"]["budgets_structures"]
    for candidate in candidates:
        previous: set[str] = set()
        for budget in budgets:
            record_ids = freeze["candidates"][candidate][str(budget)]["record_ids"]
            missing = sorted(set(record_ids) - set(by_record_id))
            if missing:
                raise ValueError(f"Frozen records are absent from the source: {missing[:5]}")
            current = set(record_ids)
            if not previous.issubset(current):
                raise ValueError(f"Candidate memberships are not nested for {candidate}")
            previous = current
            train = [by_record_id[record_id] for record_id in record_ids]
            if set(train) & set(validation):
                raise ValueError("Candidate training and checkpoint validation overlap")
            split = {"id_train": train, "id_val": validation, "id_test": internal_test}
            split_path = split_dir / f"{candidate}_n{budget}.json"
            split_path.write_text(
                json.dumps(split, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            split_hashes[str(split_path.relative_to(out_dir))] = sha256(split_path)

    runs = candidate_matrix(freeze, protocol)
    launch = {
        "schema_version": "1.0",
        "study": freeze["study"],
        "status": "launch_materialized_external_outcomes_sealed",
        "freeze_sha256": freeze["freeze_sha256"],
        "protocol_sha256": freeze["protocol_sha256"],
        "source_manifest_sha256": sha256(manifest_path),
        "released_split_sha256": sha256(released_split_path),
        "split_sha256": split_hashes,
        "runs": runs,
        "external_test_labels_inspected": False,
        "candidate_training_outcomes_exist": False,
    }
    launch["launch_sha256"] = canonical_digest(launch)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "LAUNCH_MANIFEST.json").write_text(
        json.dumps(launch, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return launch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--released-split", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    launch = materialize(
        freeze_path=args.freeze,
        protocol_path=args.protocol,
        manifest_path=args.manifest,
        released_split_path=args.released_split,
        out_dir=args.out_dir,
    )
    print(f"runs={len(launch['runs'])}")
    print(f"launch_sha256={launch['launch_sha256']}")


if __name__ == "__main__":
    main()
