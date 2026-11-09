#!/usr/bin/env python3
"""Run a bounded Nequix residual and throughput smoke on an ASE-LMDB pool."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import jax
import jraph
from nequix.data import AseDBDataset
from nequix.model import load_model
from nequix.train import evaluate


class SerialLoader:
    """Dynamic batching without forking an open ASE-LMDB handle."""

    def __init__(self, dataset, config: dict, batch_size: int):
        self.dataset = dataset
        self.n_node = max(batch_size * config["avg_n_nodes"] * 1.1, config["max_n_nodes"]) + 1
        self.n_edge = max(batch_size * config["avg_n_edges"] * 1.1, config["max_n_edges"])
        self.n_graph = batch_size + 1

    def __iter__(self):
        graphs = (self.dataset[index] for index in range(len(self.dataset)))
        return jraph.dynamically_batch(
            graphs,
            n_node=self.n_node,
            n_edge=self.n_edge,
            n_graph=self.n_graph,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    model, config = load_model(args.model)
    dataset = AseDBDataset(
        file_path=args.database,
        atomic_numbers=config["atomic_numbers"],
        cutoff=config["cutoff"],
        backend="jax",
    )
    loader = SerialLoader(dataset, config, args.batch_size)
    started = time.perf_counter()
    metrics = evaluate(
        model,
        loader,
        energy_weight=0.0,
        force_weight=20.0,
        stress_weight=5.0,
        loss_type="mae",
    )
    elapsed = time.perf_counter() - started
    result = {
        "artifact": "anarres_mlip_measurement_inference_smoke_v1",
        "records": len(dataset),
        "batch_size": args.batch_size,
        "devices": [str(device) for device in jax.devices()],
        "elapsed_seconds_including_compilation": elapsed,
        "records_per_second_including_compilation": len(dataset) / elapsed,
        "loss_contract": {
            "energy_weight": 0.0,
            "force_weight": 20.0,
            "stress_weight": 5.0,
            "loss_type": "mae",
        },
        "metrics": {key: float(value) for key, value in metrics.items()},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
