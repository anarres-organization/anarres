#!/usr/bin/env python3
"""Export identity and baseline memberships from a prepared RoboMimic copy."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py

TIERS = ("better", "okay", "worse")


def decode(values) -> list[str]:
    return [value.decode() if isinstance(value, bytes) else str(value) for value in values]


def demo_number(name: str) -> int:
    return int(name.rsplit("_", 1)[1])


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)

    with h5py.File(args.dataset, "r") as dataset:
        names = sorted(dataset["data"].keys(), key=demo_number)
        tiers = {}
        for tier in TIERS:
            for name in decode(dataset["mask"][tier][:]):
                if name in tiers:
                    raise ValueError(f"demonstration belongs to multiple tiers: {name}")
                tiers[name] = tier
        baselines = {
            "random_50": decode(dataset["mask"]["random_50_s0"][:]),
            "length_50": decode(dataset["mask"]["hlen_50"][:]),
        }
    if set(names) != set(tiers):
        raise ValueError("operator-tier masks do not cover the demonstration pool")
    if any(len(members) != 150 for members in baselines.values()):
        raise ValueError("baseline masks must each contain 150 demonstrations")

    result = {
        "dataset_sha256": sha256(args.dataset),
        "demonstrations": names,
        "tiers": tiers,
        "baselines": {key: sorted(value, key=demo_number) for key, value in baselines.items()},
        "outcomes_read": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.out), "demonstrations": len(names)}, indent=2))


if __name__ == "__main__":
    main()
