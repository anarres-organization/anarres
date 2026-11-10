#!/usr/bin/env python3
"""Create a Nequix candidate fine-tuning config from a frozen base model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def make_config(
    model_path: Path,
    train_path: Path,
    run_dir: Path,
    learning_rate: float,
    epochs: int,
    seed: int,
    validation_fraction: float,
    validation_seed: int,
) -> dict:
    with model_path.open("rb") as handle:
        base = json.loads(handle.readline().decode())
    config = dict(base)
    config["atom_energies"] = {
        int(number): value for number, value in config["atom_energies"].items()
    }
    config["kernel"] = False
    for key in (
        "shift",
        "scale",
        "avg_n_neighbors",
        "max_n_edges",
        "max_n_nodes",
        "avg_n_nodes",
        "avg_n_edges",
    ):
        config.pop(key, None)
    config.update(
        {
            "finetune_from": str(model_path),
            "train_path": str(train_path),
            "valid_frac": validation_fraction,
            "validation_seed": validation_seed,
            "state_path": str(run_dir / "latest.state.pkl"),
            "checkpoint_dir": str(run_dir / "checkpoints"),
            "optimizer": "adamw",
            "learning_rate": learning_rate,
            "warmup_epochs": 0.1,
            "warmup_factor": 0.2,
            "grad_clip_norm": 100.0,
            "weight_decay": 1.0e-3,
            "batch_size": 64,
            "n_epochs": epochs,
            "energy_weight": 0.0,
            "force_weight": 20.0,
            "stress_weight": 5.0,
            "loss_type": "mae",
            "log_every": 10,
            "ema_decay": 0.999,
            "seed": seed,
        }
    )
    return config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--learning-rate", type=float, required=True)
    parser.add_argument("--epochs", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--validation-fraction", type=float, default=0.05)
    parser.add_argument("--validation-seed", type=int, default=42)
    args = parser.parse_args()
    args.run_dir.mkdir(parents=True, exist_ok=True)
    config = make_config(
        args.model,
        args.train,
        args.run_dir,
        args.learning_rate,
        args.epochs,
        args.seed,
        args.validation_fraction,
        args.validation_seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
