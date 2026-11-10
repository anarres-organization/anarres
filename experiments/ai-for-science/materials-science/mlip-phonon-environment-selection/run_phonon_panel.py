#!/usr/bin/env python3
"""Evaluate one checkpoint over a frozen, sharded phonon target role."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def role_materials(target_roles: Path, role: str, shard_index: int, shard_count: int) -> list[str]:
    artifact = json.loads(target_roles.read_text(encoding="utf-8"))
    if role == "protected":
        role_members = artifact.get("roles", {}).get("development", []) + artifact.get(
            "roles", {}
        ).get("prospective", [])
    elif role in artifact.get("roles", {}):
        role_members = artifact["roles"][role]
    else:
        raise ValueError(f"unknown target role: {role}")
    if shard_count <= 0 or not 0 <= shard_index < shard_count:
        raise ValueError("shard index must be in [0, shard count)")
    return [
        material_id
        for ordinal, material_id in enumerate(role_members)
        if ordinal % shard_count == shard_index
    ]


def valid_result(path: Path, material_id: str) -> bool:
    if not path.exists():
        return False
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return result.get("material_id") == material_id and "metrics" in result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-roles", type=Path, required=True)
    parser.add_argument(
        "--role",
        choices=["checkpoint_qualification", "development", "prospective", "protected"],
        required=True,
    )
    parser.add_argument("--target-yaml-dir", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--backend", choices=["nequix", "mace"], required=True)
    parser.add_argument("--evaluate-script", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    args = parser.parse_args()

    materials = role_materials(args.target_roles, args.role, args.shard_index, args.shard_count)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for material_id in materials:
        output = args.output_dir / f"{material_id}.json"
        if valid_result(output, material_id):
            continue
        command = [
            sys.executable,
            str(args.evaluate_script),
            "--yaml",
            str(args.target_yaml_dir / f"{material_id}.yaml.bz2"),
            "--model",
            str(args.model),
            "--backend",
            args.backend,
            "--output",
            str(output),
        ]
        subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
