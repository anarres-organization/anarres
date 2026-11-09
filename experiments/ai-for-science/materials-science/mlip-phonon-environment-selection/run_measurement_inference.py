#!/usr/bin/env python3
"""Measure per-record Nequix residual signal over a frozen ASE-LMDB pool."""

from __future__ import annotations

import argparse
import faulthandler
import hashlib
import json
import time
from pathlib import Path

import equinox as eqx
import jax.numpy as jnp
import jraph
import numpy as np
from nequix.data import AseDBDataset
from nequix.model import load_model


class SerialSliceLoader:
    """Dynamically batch one contiguous dataset slice without worker processes."""

    def __init__(self, dataset, config: dict, batch_size: int, start: int, stop: int):
        self.dataset = dataset
        self.start = start
        self.stop = stop
        self.n_node = max(batch_size * config["avg_n_nodes"] * 1.1, config["max_n_nodes"]) + 1
        self.n_edge = max(batch_size * config["avg_n_edges"] * 1.1, config["max_n_edges"])
        self.n_graph = batch_size + 1

    def __iter__(self):
        graphs = (self.dataset[index] for index in range(self.start, self.stop))
        return jraph.dynamically_batch(
            graphs,
            n_node=self.n_node,
            n_edge=self.n_edge,
            n_graph=self.n_graph,
        )


@eqx.filter_jit
def per_graph_metrics(model, batch):
    energy, forces, stress = model(batch)
    graph_mask = jraph.get_graph_padding_mask(batch)
    node_mask = jraph.get_node_padding_mask(batch)
    graph_indices = jnp.repeat(
        jnp.arange(batch.n_node.shape[0]),
        batch.n_node,
        total_repeat_length=batch.nodes["positions"].shape[0],
    )
    valid_nodes = node_mask.astype(forces.dtype)
    node_counts = jraph.segment_sum(
        valid_nodes,
        graph_indices,
        num_segments=batch.n_node.shape[0],
        indices_are_sorted=True,
    )
    safe_counts = jnp.maximum(node_counts, 1.0)
    force_difference = forces - batch.nodes["forces"]
    force_l2 = jnp.sqrt(jnp.sum(force_difference**2, axis=-1)) * valid_nodes
    force_mae = jnp.sum(jnp.abs(force_difference), axis=-1) * valid_nodes / 3.0
    reference_force_norm = jnp.linalg.norm(batch.nodes["forces"], axis=-1) * valid_nodes
    predicted_force_norm = jnp.linalg.norm(forces, axis=-1) * valid_nodes

    def node_mean(values):
        totals = jraph.segment_sum(
            values,
            graph_indices,
            num_segments=batch.n_node.shape[0],
            indices_are_sorted=True,
        )
        return totals / safe_counts

    energy_error_per_atom = jnp.abs(energy - batch.globals["energy"]) / safe_counts
    stress_mae = jnp.mean(jnp.abs(stress - batch.globals["stress"]), axis=(1, 2))
    force_l2_mean = node_mean(force_l2)
    return {
        "graph_mask": graph_mask,
        "natoms": node_counts,
        "neighbor_edges": batch.n_edge,
        "energy_error_per_atom": energy_error_per_atom,
        "force_l2_mean": force_l2_mean,
        "force_mae": node_mean(force_mae),
        "stress_mae": stress_mae,
        "stress_mae_per_atom": stress_mae / safe_counts,
        "weighted_training_loss": 20.0 * force_l2_mean + 5.0 * stress_mae,
        "reference_force_norm_mean": node_mean(reference_force_norm),
        "predicted_force_norm_mean": node_mean(predicted_force_norm),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--stop", type=int)
    parser.add_argument("--progress-every", type=int, default=1000)
    args = parser.parse_args()

    faulthandler.enable()
    faulthandler.dump_traceback_later(120, repeat=True)
    print("loading model", flush=True)
    model, config = load_model(str(args.model))
    print("opening dataset", flush=True)
    dataset = AseDBDataset(
        file_path=str(args.database),
        atomic_numbers=config["atomic_numbers"],
        cutoff=config["cutoff"],
        backend="jax",
    )
    print(f"dataset ready: {len(dataset)} records", flush=True)
    stop = len(dataset) if args.stop is None else args.stop
    if not 0 <= args.start < stop <= len(dataset):
        raise ValueError(f"invalid slice [{args.start}, {stop}) for {len(dataset)} records")

    loader = SerialSliceLoader(dataset, config, args.batch_size, args.start, stop)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    written = 0
    totals: dict[str, float] = {}
    with args.output.open("w", encoding="utf-8") as handle:
        print("starting inference", flush=True)
        for batch in loader:
            measured = {
                key: np.asarray(value) for key, value in per_graph_metrics(model, batch).items()
            }
            valid = int(measured.pop("graph_mask").sum())
            for local_index in range(valid):
                row = {
                    "record_index": args.start + written,
                    **{
                        key: int(values[local_index])
                        if key in {"natoms", "neighbor_edges"}
                        else float(values[local_index])
                        for key, values in measured.items()
                    },
                }
                handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
                for key, value in row.items():
                    if key not in {"record_index", "natoms", "neighbor_edges"}:
                        totals[key] = totals.get(key, 0.0) + value
                written += 1
                if written % args.progress_every == 0:
                    elapsed = time.perf_counter() - started
                    print(
                        json.dumps(
                            {
                                "records": written,
                                "elapsed_seconds": elapsed,
                                "records_per_second": written / elapsed,
                            }
                        ),
                        flush=True,
                    )
    if written != stop - args.start:
        raise RuntimeError(f"wrote {written} records; expected {stop - args.start}")
    faulthandler.cancel_dump_traceback_later()

    elapsed = time.perf_counter() - started
    result = {
        "artifact": "anarres_mlip_per_record_measurement_v1",
        "database_records": len(dataset),
        "slice": {"start": args.start, "stop": stop, "records": written},
        "model_sha256": sha256(args.model),
        "output_sha256": sha256(args.output),
        "batch_size": args.batch_size,
        "loss_contract": {
            "energy_weight": 0.0,
            "force_weight": 20.0,
            "stress_weight": 5.0,
            "force_loss": "mean per-atom vector L2 residual",
            "stress_loss": "mean absolute tensor-component residual",
        },
        "elapsed_seconds_including_compilation": elapsed,
        "records_per_second_including_compilation": written / elapsed,
        "record_mean_metrics": {key: value / written for key, value in sorted(totals.items())},
    }
    args.summary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
