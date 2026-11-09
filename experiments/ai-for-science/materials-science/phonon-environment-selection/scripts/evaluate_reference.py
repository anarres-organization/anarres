#!/usr/bin/env python3
"""Evaluate a released reference checkpoint while external labels remain sealed."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

from evaluate_candidate import COMPONENTS, add_composite, load_hashed, score_batch, sha256, write_csv


def canonical_digest(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-repo", type=Path, required=True)
    parser.add_argument("--evaluation-contract", type=Path, required=True)
    parser.add_argument("--graph-cache", type=Path, required=True)
    parser.add_argument("--reference", choices=("starting_pretrained", "full_dft_posttrained"), required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()
    started = time.time()
    contract = json.loads(args.evaluation_contract.read_text(encoding="utf-8"))
    cache = load_hashed(args.graph_cache / "GRAPH_CACHE_MANIFEST.json", "graph_cache_sha256")
    if cache["external_labels_read"]:
        raise ValueError("External labels were opened before reference prediction")
    model_name = "phononscore_pretrain" if args.reference == "starting_pretrained" else "phononscore_dft"
    model_dir = args.upstream_repo / "checkpoints" / model_name
    checkpoint = model_dir / "best_model.pt"
    model_config = model_dir / "phonon_score_geom_mdn_config.json"
    fixed = json.loads((args.upstream_repo / "configs" / "fixed_scoring.json").read_text())
    reference = fixed["models"][model_name]
    if sha256(checkpoint) != reference["checkpoint_sha256"]:
        raise ValueError("Released reference checkpoint differs from fixed scoring configuration")
    output_dir = args.out_root / "_references" / args.reference
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite reference output: {output_dir}")
    output_dir.mkdir(parents=True)

    sys.path.insert(0, str(args.upstream_repo))
    sys.path.insert(0, str(args.upstream_repo / "third_party" / "alignn-main"))
    import dgl
    import torch
    from phononscore.inference.score_cifs import load_model

    model, _alignn_config, device = load_model(
        checkpoint=checkpoint,
        model_config_json=model_config,
        alignn_config_json=args.upstream_repo / "configs" / "config_min_phonon.json",
        device=args.device,
    )
    stats = reference["components"]
    outputs = []
    for panel in sorted(contract["panels"]):
        rows = []
        shards = [row for row in cache["shards"] if row["panel"] == panel]
        for shard in sorted(shards, key=lambda row: row["shard_index"]):
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
            raise ValueError(f"Incomplete reference predictions for {panel}")
        numeric_fields = (*COMPONENTS, "threshold_probability_minus_0p1")
        if not all(math.isfinite(float(row[field])) for row in rows for field in numeric_fields):
            raise ValueError(f"Non-finite reference predictions for {panel}")
        add_composite(rows, stats)
        rows.sort(key=lambda row: row["local_id"])
        path = output_dir / f"{panel}_predictions.csv"
        write_csv(path, rows)
        outputs.append({"panel": panel, "records": len(rows), "sha256": sha256(path)})
    completion = {
        "schema_version": "1.0",
        "status": "complete_reference_predictions_labels_sealed",
        "reference": args.reference,
        "model_name": model_name,
        "checkpoint_sha256": sha256(checkpoint),
        "normalization_reference": "released full-stage gradient-training moments",
        "graph_cache_sha256": cache["graph_cache_sha256"],
        "panel_outputs": outputs,
        "device": str(device),
        "wall_seconds": time.time() - started,
        "external_labels_read": False,
    }
    completion["reference_completion_sha256"] = canonical_digest(completion)
    (output_dir / "REFERENCE_COMPLETION.json").write_text(
        json.dumps(completion, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"reference={args.reference}")
    print(f"reference_completion_sha256={completion['reference_completion_sha256']}")


if __name__ == "__main__":
    main()
