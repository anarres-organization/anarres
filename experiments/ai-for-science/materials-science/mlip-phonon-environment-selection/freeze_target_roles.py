#!/usr/bin/env python3
"""Freeze outcome-blind roles for Alexandria materials unseen in MPtrj."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

SALT = "anarres-mlip-phonon-target-roles-v1"
ROLE_SIZES = {
    "checkpoint_qualification": 16,
    "development": 25,
    "prospective": 50,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_alexandria_ids(path: Path) -> set[str]:
    """Read only the identity column; no physical outcome enters the split."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames and "mp_id" in reader.fieldnames
        return {row["mp_id"] for row in reader}


def read_unseen_ids(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = payload["not_in_mptrj"] if isinstance(payload, dict) else payload
    return {str(value) for value in values}


def rank_key(material_id: str) -> str:
    return hashlib.sha256(f"{SALT}\0{material_id}".encode()).hexdigest()


def freeze_roles(alexandria_csv: Path, unseen_json: Path) -> dict:
    alexandria_ids = read_alexandria_ids(alexandria_csv)
    unseen_ids = read_unseen_ids(unseen_json)
    assert unseen_ids <= alexandria_ids
    assert len(unseen_ids) == sum(ROLE_SIZES.values()) == 91

    ranked = sorted(unseen_ids, key=lambda material_id: (rank_key(material_id), material_id))
    roles: dict[str, list[str]] = {}
    cursor = 0
    for role, size in ROLE_SIZES.items():
        roles[role] = ranked[cursor : cursor + size]
        cursor += size
    assert cursor == len(ranked)
    assert len(set().union(*(set(ids) for ids in roles.values()))) == len(ranked)

    return {
        "artifact": "anarres_mlip_phonon_target_roles_v1",
        "status": "frozen",
        "salt": SALT,
        "source": {
            "alexandria_csv_sha256": sha256(alexandria_csv),
            "mptrj_overlap_audit_sha256": sha256(unseen_json),
            "mptrj_overlap_audit_origin": (
                "atomicarchitects/nequix data/split_pbe_mdr.py at "
                "da0fb241f417dad1afafa4e723ad867667ee7445"
            ),
        },
        "eligibility": {
            "rule": "Alexandria PBE material ID absent from the MPtrj identity audit",
            "eligible_materials": len(ranked),
            "split_features_used": ["mp_id"],
        },
        "roles": roles,
        "role_hashes": {
            role: hashlib.sha256("\n".join(ids).encode()).hexdigest() for role, ids in roles.items()
        },
        "interpretation": [
            "Checkpoint qualification may use only the checkpoint_qualification outcomes.",
            "Candidate design and predictor development may use only the development outcomes.",
            (
                "Prospective outcomes remain unopened until candidate memberships, training "
                "contracts, and predictions are frozen."
            ),
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--alexandria-csv", type=Path, required=True)
    parser.add_argument("--unseen-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = freeze_roles(args.alexandria_csv, args.unseen_json)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({role: len(ids) for role, ids in result["roles"].items()}, indent=2))


if __name__ == "__main__":
    main()
