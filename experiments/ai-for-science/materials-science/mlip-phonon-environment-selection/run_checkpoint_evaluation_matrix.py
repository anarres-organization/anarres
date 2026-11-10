#!/usr/bin/env python3
"""Run one worker shard of the frozen checkpoint-by-target matrix."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def tasks(
    contract_path: Path, worker_index: int, worker_count: int, role: str = "development"
) -> list[dict]:
    if worker_count <= 0 or not 0 <= worker_index < worker_count:
        raise ValueError("worker index must be in [0, worker count)")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    matrix = [
        {
            "candidate_id": candidate["candidate_id"],
            "seed": seed,
            "epoch": epoch,
        }
        for candidate in contract["environments"][role]
        for seed in contract["randomization"]["training_seeds"]
        for epoch in contract["environment_budget"]["checkpoints_after_passes"]
    ]
    return [task for ordinal, task in enumerate(matrix) if ordinal % worker_count == worker_index]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--training-root", type=Path, required=True)
    parser.add_argument("--target-roles", type=Path, required=True)
    parser.add_argument("--target-yaml-dir", type=Path, required=True)
    parser.add_argument("--evaluate-script", type=Path, required=True)
    parser.add_argument("--panel-script", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--role", choices=["development", "prospective"], default="development")
    parser.add_argument("--worker-index", type=int, default=0)
    parser.add_argument("--worker-count", type=int, default=1)
    args = parser.parse_args()

    for task in tasks(args.contract, args.worker_index, args.worker_count, args.role):
        candidate_id = task["candidate_id"]
        seed = task["seed"]
        epoch = task["epoch"]
        model = (
            args.training_root
            / args.role
            / candidate_id
            / f"seed_{seed}"
            / "checkpoints"
            / f"epoch_{epoch:04d}.nqx"
        )
        if not model.is_file():
            raise FileNotFoundError(model)
        output = args.output_root / candidate_id / f"seed_{seed}" / f"epoch_{epoch:04d}"
        subprocess.run(
            [
                sys.executable,
                str(args.panel_script),
                "--target-roles",
                str(args.target_roles),
                "--role",
                args.role,
                "--target-yaml-dir",
                str(args.target_yaml_dir),
                "--model",
                str(model),
                "--backend",
                "nequix",
                "--evaluate-script",
                str(args.evaluate_script),
                "--output-dir",
                str(output),
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
