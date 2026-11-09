#!/usr/bin/env python3
"""Build reusable graph shards from label-blind external CIF inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path


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


def chunks(items: list[dict], size: int):
    for start in range(0, len(items), size):
        yield start // size, items[start : start + size]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-repo", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--shard-size", type=int, default=128)
    args = parser.parse_args()
    if args.shard_size <= 0:
        raise ValueError("--shard-size must be positive")
    if args.out.exists():
        raise FileExistsError(f"Refusing to overwrite graph cache: {args.out}")
    inputs = load_hashed(args.inputs / "INPUT_MANIFEST.json", "input_manifest_sha256")
    if inputs["external_labels_read"]:
        raise ValueError("Graph cache must be built before external labels are opened")

    dgl_config = args.out.parent / ".dgl"
    dgl_config.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("DGLDEFAULTDIR", str(dgl_config))
    sys.path.insert(0, str(args.upstream_repo))
    sys.path.insert(0, str(args.upstream_repo / "third_party" / "alignn-main"))
    import dgl
    import torch
    from alignn.config import TrainingConfig
    from phononscore.inference.score_cifs import build_graph_from_cif

    config = TrainingConfig(
        **json.loads((args.upstream_repo / "configs" / "config_min_phonon.json").read_text())
    )
    by_panel: dict[str, list[dict]] = {}
    for row in inputs["records"]:
        by_panel.setdefault(row["panel"], []).append(row)
    manifest_rows = []
    started = time.time()
    for panel, rows in sorted(by_panel.items()):
        rows.sort(key=lambda row: row["local_id"])
        for shard_index, shard_rows in chunks(rows, args.shard_size):
            graphs, line_graphs, lattices, ids = [], [], [], []
            for row in shard_rows:
                cif = args.inputs / panel / "cifs" / row["cif_name"]
                if sha256(cif) != row["cif_sha256"]:
                    raise ValueError(f"CIF digest differs: {panel}/{row['cif_name']}")
                _atoms, graph, line_graph, lattice, _formula = build_graph_from_cif(cif, config)
                graphs.append(graph)
                line_graphs.append(line_graph)
                lattices.append(lattice)
                ids.append(row["local_id"])
            shard_dir = args.out / panel
            shard_dir.mkdir(parents=True, exist_ok=True)
            stem = f"shard_{shard_index:04d}"
            graph_path = shard_dir / f"{stem}.graphs.bin"
            line_path = shard_dir / f"{stem}.line_graphs.bin"
            tensor_path = shard_dir / f"{stem}.lattices.pt"
            ids_path = shard_dir / f"{stem}.ids.json"
            dgl.save_graphs(str(graph_path), graphs)
            dgl.save_graphs(str(line_path), line_graphs)
            torch.save(torch.stack(lattices), tensor_path)
            ids_path.write_text(json.dumps(ids, indent=2) + "\n", encoding="utf-8")
            files = [graph_path, line_path, tensor_path, ids_path]
            manifest_rows.append(
                {
                    "panel": panel,
                    "shard_index": shard_index,
                    "records": len(ids),
                    "first_local_id": ids[0],
                    "last_local_id": ids[-1],
                    "files_sha256": {
                        str(path.relative_to(args.out)): sha256(path) for path in files
                    },
                }
            )
            print(f"panel={panel} shard={shard_index} records={len(ids)}", flush=True)
    cache = {
        "schema_version": "1.0",
        "status": "complete_label_blind_external_graph_cache",
        "input_manifest_sha256": inputs["input_manifest_sha256"],
        "external_labels_read": False,
        "shard_size": args.shard_size,
        "shards": manifest_rows,
        "wall_seconds": time.time() - started,
    }
    cache["graph_cache_sha256"] = canonical_digest(cache)
    (args.out / "GRAPH_CACHE_MANIFEST.json").write_text(
        json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"graph_cache_sha256={cache['graph_cache_sha256']}")


if __name__ == "__main__":
    main()
