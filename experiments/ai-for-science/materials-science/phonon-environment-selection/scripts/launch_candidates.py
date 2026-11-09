#!/usr/bin/env python3
"""Launch the complete frozen phonon candidate matrix and audit completion."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


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
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--workers", type=int, default=24)
    args = parser.parse_args()
    launch = load_hashed(args.launch_dir / "LAUNCH_MANIFEST.json", "launch_sha256")
    if args.out_root.exists():
        raise FileExistsError(f"Refusing to overwrite training root: {args.out_root}")
    log_dir = args.out_root / "_runner_logs"
    log_dir.mkdir(parents=True)
    runner = Path(__file__).resolve().parent / "run_candidate.py"

    def run_one(run_id: str) -> str:
        command = [
            sys.executable,
            str(runner),
            "--upstream-repo",
            str(args.upstream_repo),
            "--launch-dir",
            str(args.launch_dir),
            "--cache-dir",
            str(args.cache_dir),
            "--run-id",
            run_id,
            "--out-root",
            str(args.out_root),
            "--device",
            args.device,
        ]
        with (log_dir / f"{run_id}.log").open("w", encoding="utf-8") as log:
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
        return run_id

    started = time.time()
    run_ids = [row["run_id"] for row in launch["runs"]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(run_one, run_id) for run_id in run_ids]
        completed_ids = [future.result() for future in futures]
    completions = []
    for run_id in sorted(completed_ids):
        path = args.out_root / run_id / "COMPLETION.json"
        completion = load_hashed(path, "completion_sha256")
        if (
            completion["run_id"] != run_id
            or completion["status"] != "complete_external_outcomes_sealed"
        ):
            raise ValueError(f"Invalid completion record: {run_id}")
        completions.append(
            {
                "run_id": run_id,
                "completion_sha256": completion["completion_sha256"],
                "wall_seconds": completion["wall_seconds"],
            }
        )
    if len(completions) != 24:
        raise ValueError(f"Expected 24 completed runs, found {len(completions)}")
    manifest = {
        "schema_version": "1.0",
        "status": "all_candidate_runs_complete_external_outcomes_sealed",
        "launch_sha256": launch["launch_sha256"],
        "runs": completions,
        "orchestrator_wall_seconds": time.time() - started,
        "external_test_labels_inspected": False,
    }
    manifest["training_manifest_sha256"] = canonical_digest(manifest)
    (args.out_root / "TRAINING_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"completed={len(completions)}")
    print(f"training_manifest_sha256={manifest['training_manifest_sha256']}")


if __name__ == "__main__":
    main()
