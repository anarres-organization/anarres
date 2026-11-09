#!/usr/bin/env python3
"""Validate and summarize the full frozen MLIP measurement sweep."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def effective_coverage(masses: list[float]) -> float:
    total = sum(masses)
    return 0.0 if total <= 0 else total**2 / (len(masses) * sum(value**2 for value in masses))


def validate(manifest_path: Path, measurement_paths: list[Path], summary_paths: list[Path]) -> dict:
    manifest = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()]
    measurements = []
    for path in sorted(measurement_paths):
        measurements.extend(
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        )
    measurements.sort(key=lambda row: row["record_index"])
    summaries = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(summary_paths)]

    if len(manifest) != len(measurements):
        raise ValueError(
            f"manifest has {len(manifest)} rows; measurements have {len(measurements)}"
        )
    if [row["record_index"] for row in measurements] != list(range(len(manifest))):
        raise ValueError("measurement indices are not complete and contiguous")
    if sum(summary["slice"]["records"] for summary in summaries) != len(measurements):
        raise ValueError("shard summaries do not cover every measurement")
    model_hashes = {summary["model_sha256"] for summary in summaries}
    if len(model_hashes) != 1:
        raise ValueError(f"measurement shards use different models: {sorted(model_hashes)}")

    by_family = defaultdict(list)
    for metadata, measurement in zip(manifest, measurements, strict=True):
        if metadata["natoms"] != measurement["natoms"]:
            raise ValueError(f"atom-count mismatch at record {measurement['record_index']}")
        if measurement["natoms"] <= 0 or measurement["neighbor_edges"] < 0:
            raise ValueError(f"invalid graph cost at record {measurement['record_index']}")
        numeric = [value for key, value in measurement.items() if key != "record_index"]
        if not all(math.isfinite(value) for value in numeric):
            raise ValueError(f"non-finite measurement at record {measurement['record_index']}")
        by_family[metadata["source_family"]].append(measurement)

    family_summaries = {}
    for family, rows in sorted(by_family.items()):
        atoms = sum(row["natoms"] for row in rows)
        edges = sum(row["neighbor_edges"] for row in rows)
        masses = [
            20.0 * row["force_l2_mean"] * row["natoms"] + 5.0 * row["stress_mae"] for row in rows
        ]
        family_summaries[family] = {
            "records": len(rows),
            "atoms": atoms,
            "neighbor_edges": edges,
            "neighbor_edges_per_atom": edges / atoms,
            "signal_density_per_atom": sum(masses) / atoms,
            "effective_signal_coverage": effective_coverage(masses),
            "mean_force_mae": sum(row["force_mae"] for row in rows) / len(rows),
            "mean_stress_mae_per_atom": sum(row["stress_mae_per_atom"] for row in rows) / len(rows),
        }

    return {
        "artifact": "anarres_mlip_full_measurement_validation_v1",
        "status": "complete",
        "records": len(measurements),
        "atoms": sum(row["natoms"] for row in measurements),
        "neighbor_edges": sum(row["neighbor_edges"] for row in measurements),
        "model_sha256": next(iter(model_hashes)),
        "manifest_sha256": sha256(manifest_path),
        "measurement_sha256": {path.name: sha256(path) for path in sorted(measurement_paths)},
        "summary_sha256": {path.name: sha256(path) for path in sorted(summary_paths)},
        "source_families": family_summaries,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--measurements", type=Path, nargs="+", required=True)
    parser.add_argument("--summaries", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.manifest, args.measurements, args.summaries)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
