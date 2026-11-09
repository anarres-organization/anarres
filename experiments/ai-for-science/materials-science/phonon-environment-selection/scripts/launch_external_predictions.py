#!/usr/bin/env python3
"""Run the complete candidate prediction matrix before external labels open."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-repo", type=Path, required=True)
    parser.add_argument("--evaluation-contract", type=Path, required=True)
    parser.add_argument("--launch-dir", type=Path, required=True)
    parser.add_argument("--training-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--graph-cache", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--devices", default="cpu")
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--cpu-threads-per-worker", type=int, default=8)
    args = parser.parse_args()
    contract = json.loads(args.evaluation_contract.read_text(encoding="utf-8"))
    launch = load_hashed(args.launch_dir / "LAUNCH_MANIFEST.json", "launch_sha256")
    if args.out_root.exists():
        raise FileExistsError(f"Refusing to overwrite prediction root: {args.out_root}")
    log_dir = args.out_root / "_runner_logs"
    log_dir.mkdir(parents=True)
    dgl_config = args.out_root / "_dgl_config"
    dgl_config.mkdir(parents=True)
    devices = [value.strip() for value in args.devices.split(",") if value.strip()]
    if not devices:
        raise ValueError("At least one device is required")
    if args.cpu_threads_per_worker <= 0:
        raise ValueError("--cpu-threads-per-worker must be positive")
    runner = Path(__file__).resolve().parent / "evaluate_candidate.py"
    reference_runner = Path(__file__).resolve().parent / "evaluate_reference.py"
    run_ids = [row["run_id"] for row in launch["runs"]]
    if len(run_ids) != contract["expected_candidate_runs"]:
        raise ValueError("Launch matrix differs from the evaluation contract")

    queues = [run_ids[index::len(devices)] for index in range(len(devices))]

    def run_queue(device: str, queue: list[str]) -> list[str]:
        completed = []
        for run_id in queue:
            environment = dict(os.environ)
            environment.setdefault("DGLDEFAULTDIR", str(dgl_config))
            environment.setdefault("MPLCONFIGDIR", str(args.out_root / "_mpl_config"))
            environment["OMP_NUM_THREADS"] = str(args.cpu_threads_per_worker)
            environment["MKL_NUM_THREADS"] = str(args.cpu_threads_per_worker)
            requested_device = device
            if device != "cpu":
                environment["CUDA_VISIBLE_DEVICES"] = device
                requested_device = "cuda"
            command = [
                sys.executable,
                str(runner),
                "--upstream-repo", str(args.upstream_repo),
                "--evaluation-contract", str(args.evaluation_contract),
                "--launch-dir", str(args.launch_dir),
                "--training-root", str(args.training_root),
                "--data-root", str(args.data_root),
                "--graph-cache", str(args.graph_cache),
                "--run-id", run_id,
                "--out-root", str(args.out_root),
                "--device", requested_device,
                "--batch-size", str(args.batch_size),
            ]
            with (log_dir / f"{run_id}.log").open("w", encoding="utf-8") as log:
                subprocess.run(command, check=True, env=environment, stdout=log, stderr=subprocess.STDOUT)
            completed.append(run_id)
        return completed

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(devices)) as executor:
        futures = [executor.submit(run_queue, device, queue) for device, queue in zip(devices, queues)]
        completed = [run_id for future in futures for run_id in future.result()]
    reference_rows = []
    reference_device = devices[0]
    for reference in ("starting_pretrained", "full_dft_posttrained"):
        environment = dict(os.environ)
        environment.setdefault("DGLDEFAULTDIR", str(dgl_config))
        environment.setdefault("MPLCONFIGDIR", str(args.out_root / "_mpl_config"))
        environment["OMP_NUM_THREADS"] = str(args.cpu_threads_per_worker)
        environment["MKL_NUM_THREADS"] = str(args.cpu_threads_per_worker)
        requested_device = reference_device
        if reference_device != "cpu":
            environment["CUDA_VISIBLE_DEVICES"] = reference_device
            requested_device = "cuda"
        command = [
            sys.executable,
            str(reference_runner),
            "--upstream-repo", str(args.upstream_repo),
            "--evaluation-contract", str(args.evaluation_contract),
            "--graph-cache", str(args.graph_cache),
            "--reference", reference,
            "--out-root", str(args.out_root),
            "--device", requested_device,
            "--batch-size", str(args.batch_size),
        ]
        with (log_dir / f"reference_{reference}.log").open("w", encoding="utf-8") as log:
            subprocess.run(command, check=True, env=environment, stdout=log, stderr=subprocess.STDOUT)
        completion = load_hashed(
            args.out_root / "_references" / reference / "REFERENCE_COMPLETION.json",
            "reference_completion_sha256",
        )
        reference_rows.append(
            {
                "reference": reference,
                "reference_completion_sha256": completion["reference_completion_sha256"],
                "panel_outputs": completion["panel_outputs"],
                "wall_seconds": completion["wall_seconds"],
                "device": completion["device"],
            }
        )
    rows = []
    for run_id in sorted(completed):
        completion = load_hashed(
            args.out_root / run_id / "PREDICTION_COMPLETION.json",
            "prediction_completion_sha256",
        )
        if completion["external_labels_read"] or completion["status"] != "complete_external_predictions_labels_sealed":
            raise ValueError(f"Invalid prediction completion: {run_id}")
        rows.append(
            {
                "run_id": run_id,
                "prediction_completion_sha256": completion["prediction_completion_sha256"],
                "panel_outputs": completion["panel_outputs"],
                "wall_seconds": completion["wall_seconds"],
                "device": completion["device"],
            }
        )
    if len(rows) != contract["expected_candidate_runs"]:
        raise ValueError("Prediction matrix is incomplete")
    manifest = {
        "schema_version": "1.0",
        "status": "all_candidate_predictions_complete_external_labels_sealed",
        "evaluation_contract_sha256": hashlib.sha256(args.evaluation_contract.read_bytes()).hexdigest(),
        "graph_cache_sha256": load_hashed(
            args.graph_cache / "GRAPH_CACHE_MANIFEST.json", "graph_cache_sha256"
        )["graph_cache_sha256"],
        "runs": rows,
        "references": reference_rows,
        "external_labels_read": False,
    }
    manifest["prediction_manifest_sha256"] = canonical_digest(manifest)
    (args.out_root / "PREDICTION_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"completed={len(rows)}")
    print(f"prediction_manifest_sha256={manifest['prediction_manifest_sha256']}")


if __name__ == "__main__":
    main()
