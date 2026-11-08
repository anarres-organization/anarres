#!/usr/bin/env python3
"""Measure PhononScore signal, coverage features, and cost on training records."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

THRESHOLDS = (-0.001, -0.01, -0.1, -1.0)
EXPECTED_CHECKPOINT_SHA256 = "79b027c7037184786d6913783d3d82b081aee16f4762612184767e5ca58c0b0f"
EXPECTED_MANIFEST_SHA256 = "a4a461c887417e8d3ac8a3f67b4212cfd71ce9c0a2b9bf5ba40d1e503e26d228"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deterministic_hash(namespace: str, record_id: str) -> str:
    return hashlib.sha256(f"{namespace}|{record_id}".encode()).hexdigest()


def repeatability_ids(rows: list[dict[str, Any]], count: int = 128) -> list[str]:
    eligible = [row for row in rows if row["role"] == "gradient_train"]
    ranked = sorted(
        eligible,
        key=lambda row: (
            deterministic_hash("repeatability-v1", row["record_id"]),
            row["record_id"],
        ),
    )
    if count > len(ranked):
        raise ValueError("Repeatability sample exceeds the eligible pool")
    return [row["record_id"] for row in ranked[:count]]


def threshold_labels(value: float) -> list[float]:
    return [float(value > threshold) for threshold in THRESHOLDS]


def pool_positive_weights(rows: list[dict[str, Any]]) -> list[float]:
    eligible = [row for row in rows if row["role"] == "gradient_train"]
    if not eligible:
        raise ValueError("No gradient-training records")
    positives = [0] * len(THRESHOLDS)
    for row in eligible:
        for index, label in enumerate(threshold_labels(float(row["min_frequency"]))):
            positives[index] += int(label)
    weights = []
    for positive in positives:
        negative = len(eligible) - positive
        weights.append((negative + 1e-6) / (positive + 1e-6))
    return weights


def load_manifest(path: Path) -> list[dict[str, Any]]:
    if sha256(path) != EXPECTED_MANIFEST_SHA256:
        raise ValueError("Training manifest digest differs from the frozen protocol")
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise TypeError("Training manifest must be a list")
    return rows


def select_rows(
    rows: list[dict[str, Any]], *, record_ids_path: Path | None
) -> list[dict[str, Any]]:
    eligible = [row for row in rows if row["role"] == "gradient_train"]
    if record_ids_path is None:
        return eligible
    requested = json.loads(record_ids_path.read_text(encoding="utf-8"))
    if not isinstance(requested, list) or not all(isinstance(value, str) for value in requested):
        raise TypeError("Record-ID file must be a JSON list of strings")
    if len(requested) != len(set(requested)):
        raise ValueError("Record-ID file contains duplicates")
    by_id = {row["record_id"]: row for row in eligible}
    missing = sorted(set(requested) - set(by_id))
    if missing:
        raise ValueError(f"Requested records are not eligible: {missing[:5]}")
    return [by_id[record_id] for record_id in requested]


def chunks(items: list[Any], size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def run(args: argparse.Namespace) -> None:
    upstream = args.upstream_repo.resolve()
    data_root = args.data_root.resolve()
    checkpoint = upstream / "checkpoints" / "phononscore_pretrain" / "best_model.pt"
    model_config = (
        upstream / "checkpoints" / "phononscore_pretrain" / "phonon_score_geom_mdn_config.json"
    )
    alignn_config = upstream / "configs" / "training_dft_posttrain.json"
    manifest_path = data_root / "dft_posttrain" / "manifest.json"
    if sha256(checkpoint) != EXPECTED_CHECKPOINT_SHA256:
        raise ValueError("Starting checkpoint digest differs from the frozen protocol")

    rows = load_manifest(manifest_path)
    selected = select_rows(rows, record_ids_path=args.record_ids)
    positive_weights = pool_positive_weights(rows)
    sys.path.insert(0, str(upstream))
    sys.path.insert(0, str(upstream / "third_party" / "alignn-main"))

    import dgl
    import torch
    from phononscore.inference.score_cifs import build_graph_record, load_model
    from phononscore.models.alignn_phonon_score_geom_mdn import (
        mean_edges_by_graph,
        stable_sample_weight,
    )
    from phononscore.models.phonon_ranker_losses import mdn_negative_log_likelihood
    from torch.nn import functional as torch_functional

    model, config, device = load_model(
        checkpoint=checkpoint,
        model_config_json=model_config,
        alignn_config_json=alignn_config,
        device=args.device,
    )
    weights = torch.tensor(positive_weights, dtype=torch.float32, device=device).view(1, -1)
    thresholds = torch.tensor(THRESHOLDS, dtype=torch.float32, device=device).view(1, -1)
    output_rows: list[dict[str, Any]] = []
    build_seconds = 0.0
    inference_seconds = 0.0
    started = time.time()

    for batch_index, batch_rows in enumerate(chunks(selected, args.batch_size), start=1):
        build_start = time.time()
        records = [
            build_graph_record(data_root / "dft_posttrain" / row["cif_path"], config)
            for row in batch_rows
        ]
        build_seconds += time.time() - build_start
        graph = dgl.batch([record["graph"] for record in records]).to(device)
        line_graph = dgl.batch([record["line_graph"] for record in records]).to(device)
        lattice = torch.stack([record["lattice"] for record in records], dim=0).to(device)
        target = torch.tensor(
            [float(row["min_frequency"]) for row in batch_rows],
            dtype=torch.float32,
            device=device,
        )

        inference_start = time.time()
        with torch.no_grad():
            (
                graph_h,
                mdn_pi,
                mdn_sigma,
                mdn_mu,
                edge_distance,
                _edge_logp,
                edge_batch,
            ) = model.encode(graph, line_graph, lattice)
            prediction = model.min_freq_head(graph_h).view(-1)
            threshold_logits = model.threshold_head(graph_h)
            clipped_target = target.clamp(min=-5.0, max=0.0)
            regression = torch_functional.smooth_l1_loss(
                prediction, clipped_target, reduction="none"
            )
            labels = (target.view(-1, 1) > thresholds).to(torch.float32)
            bce = torch_functional.binary_cross_entropy_with_logits(
                threshold_logits, labels, reduction="none"
            )
            element_weights = torch.where(labels > 0.5, weights, torch.ones_like(labels))
            classification = (bce * element_weights).mean(dim=1)
            ordinal = torch_functional.relu(
                threshold_logits[:, :-1] - threshold_logits[:, 1:]
            ).mean(dim=1)
            edge_nll = mdn_negative_log_likelihood(mdn_pi, mdn_sigma, mdn_mu, edge_distance)
            mean_edge_nll = mean_edges_by_graph(
                edge_nll, edge_batch=edge_batch, num_graphs=graph_h.shape[0]
            )
            stable_weight = stable_sample_weight(target, threshold=-0.1, tau=0.2)
            geometry = stable_weight * mean_edge_nll
            signal = regression + 0.3 * classification + 0.02 * ordinal + 0.05 * geometry
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        inference_seconds += time.time() - inference_start

        embeddings = graph_h.detach().cpu().tolist()
        for index, (row, record) in enumerate(zip(batch_rows, records, strict=True)):
            output_rows.append(
                {
                    "record_id": row["record_id"],
                    "cif_id": row["id"],
                    "formula_reduced": row["formula_reduced"],
                    "min_frequency": float(row["min_frequency"]),
                    "atoms": int(record["n_atoms"]),
                    "graph_edges": int(record["graph"].num_edges()),
                    "prediction": float(prediction[index].detach().cpu()),
                    "regression_loss": float(regression[index].detach().cpu()),
                    "classification_loss": float(classification[index].detach().cpu()),
                    "ordinal_loss": float(ordinal[index].detach().cpu()),
                    "geometry_loss": float(geometry[index].detach().cpu()),
                    "singleton_objective_signal": float(signal[index].detach().cpu()),
                    "embedding": embeddings[index],
                }
            )
        completed = min(batch_index * args.batch_size, len(selected))
        print(f"measured={completed}/{len(selected)}", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for row in output_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    metadata = {
        "schema_version": "1.0",
        "protocol_status": "measurement_protocol_frozen_candidate_memberships_open",
        "records": len(output_rows),
        "record_ids_sha256": hashlib.sha256(
            "\n".join(row["record_id"] for row in output_rows).encode()
        ).hexdigest(),
        "output_sha256": sha256(args.out),
        "checkpoint_sha256": sha256(checkpoint),
        "manifest_sha256": sha256(manifest_path),
        "positive_class_weights": positive_weights,
        "device": str(device),
        "batch_size": args.batch_size,
        "build_seconds": build_seconds,
        "inference_seconds": inference_seconds,
        "total_seconds": time.time() - started,
        "external_test_labels_inspected": False,
    }
    metadata_path = args.out.with_suffix(args.out.suffix + ".metadata.json")
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"measurement={args.out}")
    print(f"metadata={metadata_path}")


def write_repeatability_ids(manifest: Path, out: Path, count: int) -> None:
    rows = load_manifest(manifest)
    identities = repeatability_ids(rows, count=count)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(identities, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-repo", type=Path)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--record-ids", type=Path)
    parser.add_argument("--write-repeatability-ids", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--repeatability-count", type=int, default=128)
    args = parser.parse_args()
    if args.write_repeatability_ids:
        if args.manifest is None:
            parser.error("--manifest is required with --write-repeatability-ids")
        write_repeatability_ids(
            args.manifest, args.write_repeatability_ids, args.repeatability_count
        )
        return
    for name in ("upstream_repo", "data_root", "out"):
        if getattr(args, name) is None:
            parser.error(f"--{name.replace('_', '-')} is required for measurement")
    if args.batch_size <= 0:
        parser.error("--batch-size must be positive")
    run(args)


if __name__ == "__main__":
    main()
