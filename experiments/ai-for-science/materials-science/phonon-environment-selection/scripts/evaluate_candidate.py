#!/usr/bin/env python3
"""Evaluate one frozen candidate checkpoint without reading external labels."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
from pathlib import Path


COMPONENTS = ("prediction", "threshold_score", "pair_geometry_score")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_digest(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def load_hashed(path: Path, field: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    stored = payload.pop(field)
    if stored != canonical_digest(payload):
        raise ValueError(f"{path.name} digest does not match its contents")
    payload[field] = stored
    return payload


def validate_model_config(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "thresholds": [-0.001, -0.01, -0.1, -1.0],
        "beta": 0.6,
        "alpha": 0.1,
        "mdn_hidden_dim": 128,
        "mdn_gaussians": 10,
        "mdn_distance_max": 8.0,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(f"Run model configuration changed at {key}")


def score_batch(model, graphs, line_graphs, lattices, device, ids):
    import dgl
    import torch

    graph = dgl.batch(graphs).to(device)
    line_graph = dgl.batch(line_graphs).to(device)
    lattice = torch.stack(lattices).to(device) if isinstance(lattices, list) else lattices.to(device)
    with torch.no_grad():
        out = model([graph, line_graph, lattice])
        threshold_probabilities = torch.sigmoid(out.threshold_logits).detach().cpu().tolist()
    values = {
        "prediction": out.min_freq.detach().cpu().view(-1).tolist(),
        "threshold_score": out.threshold_score.detach().cpu().view(-1).tolist(),
        "pair_geometry_score": out.pair_geometry_score.detach().cpu().view(-1).tolist(),
    }
    return [
        {
            "local_id": local_id,
            **{key: float(values[key][index]) for key in COMPONENTS},
            "threshold_probability_minus_0p1": float(threshold_probabilities[index][2]),
        }
        for index, local_id in enumerate(ids)
    ]


def moments(rows: list[dict]) -> dict:
    result = {}
    for component in COMPONENTS:
        values = [float(row[component]) for row in rows]
        if not values or not all(math.isfinite(value) for value in values):
            raise ValueError(f"Invalid normalization values for {component}")
        mean = math.fsum(values) / len(values)
        variance = math.fsum((value - mean) ** 2 for value in values) / len(values)
        if variance <= 0:
            raise ValueError(f"Cannot normalize constant component: {component}")
        result[component] = {"mean": mean, "variance": variance, "std": math.sqrt(variance)}
    return result


def add_composite(rows: list[dict], stats: dict) -> None:
    for row in rows:
        z = {
            key: (float(row[key]) - stats[key]["mean"]) / stats[key]["std"]
            for key in COMPONENTS
        }
        row["composite_score"] = z["prediction"] + 0.5 * z["threshold_score"] + 0.2 * z["pair_geometry_score"]


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = ["local_id", *COMPONENTS, "threshold_probability_minus_0p1", "composite_score"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-repo", type=Path, required=True)
    parser.add_argument("--evaluation-contract", type=Path, required=True)
    parser.add_argument("--launch-dir", type=Path, required=True)
    parser.add_argument("--training-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--graph-cache", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()
    started = time.time()
    contract = json.loads(args.evaluation_contract.read_text(encoding="utf-8"))
    launch = load_hashed(args.launch_dir / "LAUNCH_MANIFEST.json", "launch_sha256")
    training = load_hashed(args.training_root / "TRAINING_MANIFEST.json", "training_manifest_sha256")
    cache = load_hashed(args.graph_cache / "GRAPH_CACHE_MANIFEST.json", "graph_cache_sha256")
    if training["training_manifest_sha256"] != contract["training_manifest_sha256"]:
        raise ValueError("Training manifest differs from frozen evaluation contract")
    if launch["launch_sha256"] != contract["launch_sha256"]:
        raise ValueError("Launch manifest differs from frozen evaluation contract")
    if cache["external_labels_read"]:
        raise ValueError("External labels were opened before prediction completion")
    runs = [row for row in launch["runs"] if row["run_id"] == args.run_id]
    if len(runs) != 1:
        raise ValueError(f"Unknown or duplicate run: {args.run_id}")
    run = runs[0]
    completion_rows = [row for row in training["runs"] if row["run_id"] == args.run_id]
    if len(completion_rows) != 1:
        raise ValueError("Training manifest does not contain the requested run")
    run_dir = args.training_root / args.run_id
    completion = load_hashed(run_dir / "COMPLETION.json", "completion_sha256")
    if completion["completion_sha256"] != completion_rows[0]["completion_sha256"]:
        raise ValueError("Completion record differs from sealed training manifest")
    checkpoint = run_dir / "best_model.pt"
    if sha256(checkpoint) != completion["output_sha256"]["best_model.pt"]:
        raise ValueError("Candidate checkpoint differs from sealed completion record")
    model_config = run_dir / "phonon_score_geom_mdn_config.json"
    validate_model_config(model_config)
    output_dir = args.out_root / args.run_id
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite evaluation output: {output_dir}")
    output_dir.mkdir(parents=True)

    sys.path.insert(0, str(args.upstream_repo))
    sys.path.insert(0, str(args.upstream_repo / "third_party" / "alignn-main"))
    import dgl
    import torch
    from phononscore.inference.score_cifs import build_graph_from_cif, load_model

    model, alignn_config, device = load_model(
        checkpoint=checkpoint,
        model_config_json=model_config,
        alignn_config_json=args.upstream_repo / "configs" / "config_min_phonon.json",
        device=args.device,
    )
    split = json.loads((args.launch_dir / run["split_file"]).read_text(encoding="utf-8"))
    train_ids = split["id_train"]
    if len(train_ids) != run["expected_train_records"] or len(train_ids) != len(set(train_ids)):
        raise ValueError("Candidate training identities differ from the launch contract")
    train_rows = []
    for start in range(0, len(train_ids), args.batch_size):
        batch_ids = train_ids[start : start + args.batch_size]
        graphs, lines, lattices = [], [], []
        for local_path in batch_ids:
            cif = args.data_root / "dft_posttrain" / local_path
            _atoms, graph, line_graph, lattice, _formula = build_graph_from_cif(cif, alignn_config)
            graphs.append(graph)
            lines.append(line_graph)
            lattices.append(lattice)
        train_rows.extend(
            score_batch(model, graphs, lines, lattices, device, [Path(value).stem for value in batch_ids])
        )
    stats = moments(train_rows)
    stats_payload = {
        "schema_version": "1.0",
        "run_id": args.run_id,
        "records": len(train_rows),
        "reference": "exact frozen candidate training subset",
        "ddof": 0,
        "checkpoint_sha256": sha256(checkpoint),
        "components": stats,
    }
    stats_payload["normalization_sha256"] = canonical_digest(stats_payload)
    stats_path = output_dir / "NORMALIZATION.json"
    stats_path.write_text(json.dumps(stats_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    panel_outputs = []
    for panel in sorted(contract["panels"]):
        rows = []
        shards = [row for row in cache["shards"] if row["panel"] == panel]
        for shard in sorted(shards, key=lambda row: row["shard_index"]):
            files = shard["files_sha256"]
            for relative, digest in files.items():
                if sha256(args.graph_cache / relative) != digest:
                    raise ValueError(f"Graph-cache shard differs: {relative}")
            stem = args.graph_cache / panel / f"shard_{shard['shard_index']:04d}"
            graphs, _ = dgl.load_graphs(str(stem.with_suffix(".graphs.bin")))
            lines, _ = dgl.load_graphs(str(stem.with_suffix(".line_graphs.bin")))
            lattices = torch.load(stem.with_suffix(".lattices.pt"), map_location="cpu", weights_only=True)
            ids = json.loads(stem.with_suffix(".ids.json").read_text(encoding="utf-8"))
            for start in range(0, len(ids), args.batch_size):
                stop = start + args.batch_size
                rows.extend(
                    score_batch(model, graphs[start:stop], lines[start:stop], lattices[start:stop], device, ids[start:stop])
                )
        expected = contract["panels"][panel]["records"]
        if len(rows) != expected or len({row["local_id"] for row in rows}) != expected:
            raise ValueError(f"Incomplete or duplicate predictions for {panel}")
        if not all(math.isfinite(float(row[key])) for row in rows for key in (*COMPONENTS, "threshold_probability_minus_0p1")):
            raise ValueError(f"Non-finite predictions for {panel}")
        add_composite(rows, stats)
        rows.sort(key=lambda row: row["local_id"])
        path = output_dir / f"{panel}_predictions.csv"
        write_csv(path, rows)
        panel_outputs.append({"panel": panel, "records": len(rows), "sha256": sha256(path)})
    result = {
        "schema_version": "1.0",
        "status": "complete_external_predictions_labels_sealed",
        "run": run,
        "completion_sha256": completion["completion_sha256"],
        "checkpoint_sha256": sha256(checkpoint),
        "normalization_sha256": stats_payload["normalization_sha256"],
        "graph_cache_sha256": cache["graph_cache_sha256"],
        "panel_outputs": panel_outputs,
        "device": str(device),
        "wall_seconds": time.time() - started,
        "external_labels_read": False,
    }
    result["prediction_completion_sha256"] = canonical_digest(result)
    (output_dir / "PREDICTION_COMPLETION.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"run_id={args.run_id}")
    print(f"prediction_completion_sha256={result['prediction_completion_sha256']}")


if __name__ == "__main__":
    main()
