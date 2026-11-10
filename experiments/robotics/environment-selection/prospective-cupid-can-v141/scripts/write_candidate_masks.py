#!/usr/bin/env python3
"""Write frozen candidate memberships to a copied RoboMimic dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np

MASK_KEYS = {
    "random_50": "anarres_random_50",
    "length_50": "anarres_length_50",
    "cupid_50": "anarres_cupid_50",
    "cupid_tier_balanced_50": "anarres_cupid_tier_balanced_50",
}


def demo_number(name: str) -> int:
    return int(name.rsplit("_", 1)[1])


def membership_hash(names: list[str]) -> str:
    payload = "\n".join(sorted(names, key=demo_number)) + "\n"
    return hashlib.sha256(payload.encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    args = parser.parse_args()
    frozen = json.loads(args.candidates.read_text())
    if frozen["status"] != "CANDIDATES_FROZEN__OUTCOMES_UNOPENED":
        raise ValueError("candidate artifact is not frozen")
    if frozen["outcomes_read"]:
        raise ValueError("candidate artifact reports outcome access")

    with h5py.File(args.dataset, "a") as dataset:
        if "mask" not in dataset:
            dataset.create_group("mask")
        known = set(dataset["data"].keys())
        for candidate_id, mask_key in MASK_KEYS.items():
            record = frozen["candidates"][candidate_id]
            members = sorted(record["members"], key=demo_number)
            if membership_hash(members) != record["membership_sha256"]:
                raise ValueError(f"membership hash mismatch for {candidate_id}")
            if set(members) - known:
                raise ValueError(f"unknown demonstration in {candidate_id}")
            if mask_key in dataset["mask"]:
                del dataset["mask"][mask_key]
            dataset["mask"].create_dataset(mask_key, data=np.array(members, dtype="S"))
    print(json.dumps({"dataset": str(args.dataset), "masks": MASK_KEYS}, indent=2))


if __name__ == "__main__":
    main()
