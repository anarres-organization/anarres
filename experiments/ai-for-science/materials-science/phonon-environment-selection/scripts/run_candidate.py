#!/usr/bin/env python3
"""Run one frozen PhononScore candidate and write an audited completion record."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_hashed(path: Path, field: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    stored = payload.pop(field)
    if stored != canonical_digest(payload):
        raise ValueError(f"{path.name} digest does not match its contents")
    payload[field] = stored
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-repo", type=Path, required=True)
    parser.add_argument("--launch-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    launch = load_hashed(args.launch_dir / "LAUNCH_MANIFEST.json", "launch_sha256")
    caches = load_hashed(args.cache_dir / "CACHE_MANIFEST.json", "cache_manifest_sha256")
    if launch["external_test_labels_inspected"] or caches["external_test_labels_inspected"]:
        raise ValueError("External labels must remain sealed during candidate training")
    if caches["launch_sha256"] != launch["launch_sha256"]:
        raise ValueError("Cache manifest is not bound to the launch manifest")
    matches = [row for row in launch["runs"] if row["run_id"] == args.run_id]
    if len(matches) != 1:
        raise ValueError(f"Unknown or duplicate run ID: {args.run_id}")
    run = matches[0]
    cache_id = Path(run["split_file"]).stem
    cache_rows = [row for row in caches["caches"] if row["cache_id"] == cache_id]
    if len(cache_rows) != 1 or cache_rows[0]["status"] != "complete":
        raise ValueError(f"Candidate cache is unavailable: {cache_id}")
    out_dir = args.out_root / args.run_id
    if out_dir.exists():
        raise FileExistsError(f"Refusing to overwrite run directory: {out_dir}")
    out_dir.mkdir(parents=True)
    upstream = args.upstream_repo
    prefix = args.cache_dir / cache_id / "lmdb" / "graphs_"
    ids_path = args.cache_dir / cache_id / "lmdb" / "ids_train_val_test.json"
    command = [
        sys.executable,
        "-m",
        "phononscore.training.train",
        "--alignn_src",
        str(upstream / "third_party" / "alignn-main"),
        "--config",
        str(upstream / "configs" / "training_dft_posttrain.json"),
        "--lmdb_prefix",
        str(prefix),
        "--ids_json",
        str(ids_path),
        "--out_dir",
        str(out_dir),
        "--epochs",
        "100",
        "--batch_size",
        "96",
        "--num_workers",
        "0",
        "--learning_rate",
        "0.0003",
        "--weight_decay",
        "0.00001",
        "--thresholds=-0.001,-0.01,-0.1,-1.0",
        "--reg_target_mode",
        "clip5",
        "--beta",
        "0.6",
        "--alpha",
        "0.1",
        "--lambda_cls",
        "0.3",
        "--lambda_rank",
        "0.3",
        "--lambda_ordinal",
        "0.02",
        "--lambda_mdn",
        "0.05",
        "--lambda_geom_rank",
        "0.05",
        "--cls_loss",
        "balanced_bce",
        "--rank_loss",
        "threshold_aware",
        "--max_rank_pairs",
        "4096",
        "--mdn_hidden_dim",
        "128",
        "--mdn_gaussians",
        "10",
        "--mdn_distance_max",
        "8.0",
        "--stable_threshold",
        "-0.1",
        "--stable_tau",
        "0.2",
        "--seed",
        str(run["seed"]),
        "--save_every",
        "100",
        "--device",
        args.device,
        "--restart_encoder",
        str(upstream / "checkpoints" / "phononscore_pretrain" / "best_model.pt"),
    ]
    contract = {
        "schema_version": "1.0",
        "run": run,
        "launch_sha256": launch["launch_sha256"],
        "cache_manifest_sha256": caches["cache_manifest_sha256"],
        "device": args.device,
        "epochs": 100,
        "batch_size": 96,
        "external_test_labels_inspected": False,
    }
    contract["contract_sha256"] = canonical_digest(contract)
    (out_dir / "RUN_CONTRACT.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        [
            str(upstream),
            str(upstream / "third_party" / "alignn-main"),
            environment.get("PYTHONPATH", ""),
        ]
    )
    started = time.time()
    with (out_dir / "train.log").open("w", encoding="utf-8") as log:
        subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT, env=environment)
    history = json.loads((out_dir / "history.json").read_text(encoding="utf-8"))
    if len(history) != 100:
        raise ValueError(f"Expected 100 epochs, found {len(history)}")
    required = [
        "best_model.pt",
        "current_model.pt",
        "test_metrics.json",
        "prediction_results_test_set.csv",
    ]
    missing = [name for name in required if not (out_dir / name).is_file()]
    if missing:
        raise ValueError(f"Run outputs are incomplete: {missing}")
    completion = {
        "schema_version": "1.0",
        "run_id": args.run_id,
        "contract_sha256": contract["contract_sha256"],
        "epochs": len(history),
        "wall_seconds": time.time() - started,
        "output_sha256": {name: sha256(out_dir / name) for name in required},
        "status": "complete_external_outcomes_sealed",
        "external_test_labels_inspected": False,
    }
    completion["completion_sha256"] = canonical_digest(completion)
    (out_dir / "COMPLETION.json").write_text(
        json.dumps(completion, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"run_id={args.run_id}")
    print(f"completion_sha256={completion['completion_sha256']}")


if __name__ == "__main__":
    main()
