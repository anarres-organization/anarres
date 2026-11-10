#!/usr/bin/env python3
"""Run a deterministic shard of the frozen candidate-training matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tasks(
    contract_path: Path,
    role: str,
    worker_index: int,
    worker_count: int,
    prospective_authorized: bool = False,
) -> list[dict]:
    if worker_count <= 0 or not 0 <= worker_index < worker_count:
        raise ValueError("worker index must be in [0, worker count)")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if role == "prospective" and not prospective_authorized:
        raise ValueError("prospective training remains blocked until predictions are frozen")
    matrix = [
        {"candidate_id": candidate["candidate_id"], "seed": seed}
        for candidate in contract["environments"][role]
        for seed in contract["randomization"]["training_seeds"]
    ]
    return [task for ordinal, task in enumerate(matrix) if ordinal % worker_count == worker_index]


def complete(run_dir: Path, passes: int) -> bool:
    checkpoints = run_dir / "checkpoints"
    return all(
        (checkpoints / f"epoch_{epoch:04d}.nqx").is_file()
        and (checkpoints / f"epoch_{epoch:04d}.state.pkl").is_file()
        for epoch in range(1, passes + 1)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--role", choices=["development", "prospective"], required=True)
    parser.add_argument("--environment-dir", type=Path, required=True)
    parser.add_argument("--base-model", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--config-generator", type=Path, required=True)
    parser.add_argument("--training-source", type=Path, required=True)
    parser.add_argument("--prospective-authorization", type=Path)
    parser.add_argument("--worker-index", type=int, default=0)
    parser.add_argument("--worker-count", type=int, default=1)
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    passes = contract["environment_budget"]["passes"]
    learning_rate = contract["optimization"]["learning_rate"]
    prospective_authorized = False
    if args.role == "prospective":
        if args.prospective_authorization is None:
            raise ValueError("prospective training requires a frozen forecast authorization")
        authorization = json.loads(args.prospective_authorization.read_text(encoding="utf-8"))
        prospective_authorized = authorization.get(
            "status"
        ) == "prospective_predictions_frozen" and authorization.get(
            "final_training_contract_sha256"
        ) == sha256(args.contract)
        if not prospective_authorized:
            raise ValueError("prospective authorization does not bind the frozen contract")
    for task in tasks(
        args.contract,
        args.role,
        args.worker_index,
        args.worker_count,
        prospective_authorized,
    ):
        candidate_id = task["candidate_id"]
        seed = task["seed"]
        run_dir = args.output_root / args.role / candidate_id / f"seed_{seed}"
        if complete(run_dir, passes):
            continue
        run_dir.mkdir(parents=True, exist_ok=True)
        config = run_dir / "config.yml"
        subprocess.run(
            [
                sys.executable,
                str(args.config_generator),
                "--model",
                str(args.base_model),
                "--train",
                str(args.environment_dir / f"{candidate_id}.aselmdb"),
                "--run-dir",
                str(run_dir),
                "--output",
                str(config),
                "--learning-rate",
                str(learning_rate),
                "--epochs",
                str(passes),
                "--seed",
                str(seed),
                "--validation-fraction",
                str(contract["randomization"]["validation_fraction"]),
                "--validation-seed",
                str(contract["randomization"]["validation_seed"]),
            ],
            check=True,
        )
        environment = dict(os.environ)
        environment["PYTHONHASHSEED"] = str(contract["randomization"]["python_hash_seed"])
        with (run_dir / "train.log").open("a", encoding="utf-8") as log:
            subprocess.run(
                [sys.executable, "-m", "nequix.train", str(config)],
                cwd=args.training_source,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )
        if not complete(run_dir, passes):
            raise RuntimeError(f"training did not produce the frozen checkpoint set: {run_dir}")


if __name__ == "__main__":
    main()
