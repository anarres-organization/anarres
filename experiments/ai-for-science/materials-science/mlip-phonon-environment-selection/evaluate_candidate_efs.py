#!/usr/bin/env python3
"""Evaluate a Nequix checkpoint on a deterministic candidate holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def evaluate_holdout(
    dataset_path: Path,
    model_path: Path,
    validation_fraction: float,
    validation_seed: int,
    batch_size: int,
) -> dict:
    from nequix.data import AseDBDataset, DataLoader, dataset_stats
    from nequix.model import load_model
    from nequix.train import evaluate

    model, model_config = load_model(model_path)
    dataset = AseDBDataset(
        file_path=str(dataset_path),
        atomic_numbers=model_config["atomic_numbers"],
        cutoff=model_config["cutoff"],
    )
    train_dataset, validation_dataset = dataset.split(
        valid_frac=validation_fraction, seed=validation_seed
    )
    atom_energies = [
        model_config["atom_energies"][str(number)] for number in model_config["atomic_numbers"]
    ]
    stats = dataset_stats(train_dataset, atom_energies)
    loader = DataLoader(
        validation_dataset,
        batch_size=batch_size,
        shuffle=False,
        max_n_nodes=stats["max_n_nodes"],
        max_n_edges=stats["max_n_edges"],
        avg_n_nodes=stats["avg_n_nodes"],
        avg_n_edges=stats["avg_n_edges"],
        num_workers=8,
    )
    metrics = evaluate(
        model,
        loader,
        energy_weight=0.0,
        force_weight=20.0,
        stress_weight=5.0,
        loss_type="mae",
    )
    return {
        "artifact": "anarres_mlip_candidate_efs_evaluation_v1",
        "dataset_sha256": sha256(dataset_path),
        "model_sha256": sha256(model_path),
        "records": {
            "total": len(dataset),
            "training": len(train_dataset),
            "validation": len(validation_dataset),
        },
        "split": {
            "validation_fraction": validation_fraction,
            "validation_seed": validation_seed,
        },
        "loss_contract": {
            "energy_weight": 0.0,
            "force_weight": 20.0,
            "stress_weight": 5.0,
            "loss_type": "mae",
        },
        "metrics": {key: float(value) for key, value in metrics.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validation-fraction", type=float, default=0.05)
    parser.add_argument("--validation-seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    result = evaluate_holdout(
        args.dataset,
        args.model,
        args.validation_fraction,
        args.validation_seed,
        args.batch_size,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
