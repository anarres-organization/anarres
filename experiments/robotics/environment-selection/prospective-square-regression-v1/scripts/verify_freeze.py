#!/usr/bin/env python3
"""Verify the outcome-blind Square protocol and fixed-state freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify() -> dict:
    freeze = json.loads((ROOT / "FREEZE.json").read_text(encoding="utf-8"))
    protocol = json.loads((ROOT / "PROTOCOL.json").read_text(encoding="utf-8"))
    state_bank = json.loads((ROOT / "STATE_BANK.json").read_text(encoding="utf-8"))
    if freeze.get("candidate_outcomes_opened") is not False:
        raise ValueError("freeze must precede candidate outcomes")
    if protocol["study_id"] != freeze["study_id"] or state_bank["study_id"] != freeze["study_id"]:
        raise ValueError("study identities differ")
    for name, expected in freeze["artifacts"].items():
        if sha256(ROOT / name) != expected:
            raise ValueError(f"frozen artifact differs: {name}")
    if state_bank["state_bank_sha256"] != freeze["artifacts"]["STATE_BANK.hdf5"]:
        raise ValueError("state-bank manifest and freeze disagree")
    if state_bank["source_dataset_sha256"] != protocol["source"]["dataset_sha256"]:
        raise ValueError("dataset identity differs between protocol and state bank")
    if state_bank["states"] != protocol["state_bank"]["states"]:
        raise ValueError("state count differs between protocol and state bank")
    if set(state_bank["stratum_counts"]) != {str(index) for index in range(8)}:
        raise ValueError("state bank does not contain all eight frozen strata")
    if sum(state_bank["stratum_counts"].values()) != state_bank["states"]:
        raise ValueError("stratum counts do not sum to the state count")
    return {
        "study_id": freeze["study_id"],
        "status": freeze["status"],
        "states": state_bank["states"],
        "strata": len(state_bank["stratum_counts"]),
        "candidate_outcomes_opened": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
