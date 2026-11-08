#!/usr/bin/env python3
"""Create or verify an outcome-blind commitment to private scenario seeds."""

from __future__ import annotations

import argparse
import hashlib
import json
import string
from pathlib import Path

EXPECTED_STUDY = "prospective_finance_environment_selection_v1"
EXPECTED_REVISION = "0d09882b59a16f190feac09abc9331a733a6f96b"
PRIVATE_PARTITIONS = ("candidate", "held_out")


def canonical_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def validate_private_panel(payload: dict) -> None:
    if payload.get("schema_version") != 1:
        raise ValueError("private panel schema_version must be 1")
    if payload.get("study_id") != EXPECTED_STUDY:
        raise ValueError("private panel has the wrong study_id")
    if payload.get("source_revision") != EXPECTED_REVISION:
        raise ValueError("private panel has the wrong source revision")
    nonce = payload.get("nonce")
    if (
        not isinstance(nonce, str)
        or len(nonce) != 64
        or any(character not in string.hexdigits for character in nonce)
    ):
        raise ValueError("nonce must be 32 random bytes encoded as 64 hex characters")
    partitions = payload.get("partitions")
    if not isinstance(partitions, dict) or set(partitions) != set(PRIVATE_PARTITIONS):
        raise ValueError("private panel must contain candidate and held_out partitions")
    seen: set[int] = set()
    for name in PRIVATE_PARTITIONS:
        seeds = partitions[name]
        if not isinstance(seeds, list) or not seeds:
            raise ValueError(f"{name} must contain at least one seed")
        if any(type(seed) is not int or seed < 0 for seed in seeds):
            raise ValueError(f"{name} seeds must be non-negative integers")
        if len(seeds) != len(set(seeds)):
            raise ValueError(f"{name} contains duplicate seeds")
        if seen & set(seeds):
            raise ValueError("candidate and held_out seeds must be disjoint")
        seen.update(seeds)


def commitment(payload: dict) -> dict:
    validate_private_panel(payload)
    return {
        "schema_version": 1,
        "study_id": payload["study_id"],
        "source_revision": payload["source_revision"],
        "algorithm": "sha256-canonical-json-with-256-bit-private-nonce",
        "partition_counts": {name: len(payload["partitions"][name]) for name in PRIVATE_PARTITIONS},
        "commitment_sha256": hashlib.sha256(canonical_bytes(payload)).hexdigest(),
        "identities_disclosed": False,
    }


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("commit")
    create.add_argument("private_panel", type=Path)
    verify = subparsers.add_parser("verify")
    verify.add_argument("private_panel", type=Path)
    verify.add_argument("public_commitment", type=Path)
    args = parser.parse_args()

    observed = commitment(load(args.private_panel))
    if args.command == "commit":
        print(json.dumps(observed, indent=2, sort_keys=True))
        return
    expected = load(args.public_commitment)
    if observed != expected:
        raise SystemExit("panel commitment does not match")
    print("panel commitment verified")


if __name__ == "__main__":
    main()
