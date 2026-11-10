#!/usr/bin/env python3
"""Evaluate one checkpoint over a frozen target role with one model load."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def load_module(path: Path):
    specification = importlib.util.spec_from_file_location("anarres_evaluate_phonon", path)
    if specification is None or specification.loader is None:
        raise ValueError(f"cannot load evaluator: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def role_materials(target_roles: Path, role: str) -> list[str]:
    artifact = json.loads(target_roles.read_text(encoding="utf-8"))
    if role not in artifact["roles"]:
        raise ValueError(f"unknown target role: {role}")
    return artifact["roles"][role]


def valid_result(path: Path, material_id: str, model_digest: str) -> bool:
    if not path.exists():
        return False
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        result.get("material_id") == material_id
        and result.get("model_sha256") == model_digest
        and "metrics" in result
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-roles", type=Path, required=True)
    parser.add_argument(
        "--role",
        choices=["checkpoint_qualification", "development", "prospective"],
        required=True,
    )
    parser.add_argument("--target-yaml-dir", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--backend", choices=["nequix", "mace"], required=True)
    parser.add_argument("--evaluate-script", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    evaluator = load_module(args.evaluate_script)
    model_digest = evaluator.sha256(args.model)
    calculator = evaluator.load_calculator(args.backend, args.model)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for material_id in role_materials(args.target_roles, args.role):
        output = args.output_dir / f"{material_id}.json"
        if valid_result(output, material_id, model_digest):
            continue
        result = evaluator.evaluate(
            args.target_yaml_dir / f"{material_id}.yaml.bz2",
            args.model,
            args.backend,
            0.01,
            0.005,
            500,
            calculator=calculator,
            model_digest=model_digest,
        )
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
