#!/usr/bin/env python3
"""Build and audit LMDB caches for every frozen phonon candidate split."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
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


def load_launch(path: Path) -> dict[str, Any]:
    launch = json.loads(path.read_text(encoding="utf-8"))
    stored = launch.pop("launch_sha256")
    if stored != canonical_digest(launch):
        raise ValueError("Launch manifest digest does not match its contents")
    launch["launch_sha256"] = stored
    if launch["external_test_labels_inspected"]:
        raise ValueError("External labels must remain sealed during cache construction")
    return launch


def build_one(
    *,
    split_rel: str,
    split_sha256: str,
    launch_dir: Path,
    upstream: Path,
    data_root: Path,
    out_dir: Path,
) -> dict[str, Any]:
    split_path = launch_dir / split_rel
    if sha256(split_path) != split_sha256:
        raise ValueError(f"Split digest changed: {split_rel}")
    cache_id = Path(split_rel).stem
    cache_dir = out_dir / cache_id
    if cache_dir.exists():
        raise FileExistsError(f"Refusing to overwrite candidate cache: {cache_dir}")
    (cache_dir / "lmdb").mkdir(parents=True)
    prefix = cache_dir / "lmdb" / "graphs_"
    ids_path = cache_dir / "lmdb" / "ids_train_val_test.json"
    command = [
        sys.executable,
        "-m",
        "phononscore.training.build_lmdb",
        "--alignn_src",
        str(upstream / "third_party" / "alignn-main"),
        "--dataset_dir",
        str(data_root / "dft_posttrain"),
        "--config",
        str(upstream / "configs" / "training_dft_posttrain.json"),
        "--lmdb_prefix",
        str(prefix),
        "--ids_json",
        str(ids_path),
        "--split_ids",
        str(split_path),
    ]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        [
            str(upstream),
            str(upstream / "third_party" / "alignn-main"),
            environment.get("PYTHONPATH", ""),
        ]
    )
    with (cache_dir / "build.log").open("w", encoding="utf-8") as log:
        subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT, env=environment)
    expected = json.loads(split_path.read_text(encoding="utf-8"))
    observed = json.loads(ids_path.read_text(encoding="utf-8"))
    if observed != expected:
        raise ValueError(f"Built cache identities differ from the frozen split: {cache_id}")
    return {
        "cache_id": cache_id,
        "split_file": split_rel,
        "split_sha256": split_sha256,
        "ids_sha256": sha256(ids_path),
        "train_records": len(observed["id_train"]),
        "validation_records": len(observed["id_val"]),
        "internal_test_records": len(observed["id_test"]),
        "status": "complete",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-repo", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--launch-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    launch = load_launch(args.launch_dir / "LAUNCH_MANIFEST.json")
    if args.out_dir.exists():
        raise FileExistsError(f"Refusing to overwrite cache root: {args.out_dir}")
    args.out_dir.mkdir(parents=True)
    splits = sorted(launch["split_sha256"].items())
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                build_one,
                split_rel=split_rel,
                split_sha256=digest,
                launch_dir=args.launch_dir,
                upstream=args.upstream_repo,
                data_root=args.data_root,
                out_dir=args.out_dir,
            )
            for split_rel, digest in splits
        ]
        caches = [future.result() for future in futures]
    manifest = {
        "schema_version": "1.0",
        "status": "candidate_caches_complete_external_outcomes_sealed",
        "launch_sha256": launch["launch_sha256"],
        "caches": sorted(caches, key=lambda row: row["cache_id"]),
        "external_test_labels_inspected": False,
    }
    manifest["cache_manifest_sha256"] = canonical_digest(manifest)
    (args.out_dir / "CACHE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"caches={len(caches)}")
    print(f"cache_manifest_sha256={manifest['cache_manifest_sha256']}")


if __name__ == "__main__":
    main()
