#!/usr/bin/env python3
"""Build matched downstream panels from Zhang et al. (2023) ET-AL results."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path


SOURCE_ID = "zhang_2023_etal"
REVISION = "9cc7ca8e632a31dba366a309817d24de09404766"
RESULT_SHA256 = "ca4efc2934ef9055b2fc631b3d703f01d6ecf4aef9d2590fb686f07a174f312b"
ENTROPY_SHA256 = "0115bc1a60be8a7fc6dd3bbc6097f1616a3dabd915372a82359ea5a1446e4256"
ENVIRONMENTS = {
    "etal": {
        "uses_entropy_targeting": 1,
        "targets_underrepresented_structure_space": 1,
        "adaptive_acquisition": 1,
    },
    "rand": {
        "uses_entropy_targeting": 0,
        "targets_underrepresented_structure_space": 0,
        "adaptive_acquisition": 0,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ingest(repository: Path) -> dict:
    result_path = repository / "results" / "ML_r2.csv"
    entropy_path = repository / "results" / "info_entropy_evolution.csv"
    if sha256(result_path) != RESULT_SHA256:
        raise ValueError("checksum mismatch for ML_r2.csv")
    if sha256(entropy_path) != ENTROPY_SHA256:
        raise ValueError("checksum mismatch for info_entropy_evolution.csv")

    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    with result_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            grouped[(row["model"], row["target"], row["dataset"])].append(float(row["r2"]))

    models = sorted({key[0] for key in grouped})
    targets = sorted({key[1] for key in grouped})
    if models != ["gb-B", "gb-G", "rf-B", "rf-G"]:
        raise ValueError(f"unexpected model identities: {models}")
    if targets != ["B", "G"]:
        raise ValueError(f"unexpected targets: {targets}")
    if any(len(values) != 30 for values in grouped.values()):
        raise ValueError("expected 30 released fits per model, target, and environment")

    arms = []
    for model in models:
        target = model.rsplit("-", 1)[1]
        panel_id = f"{SOURCE_ID}:{target}:{model.split('-', 1)[0]}:test_r2"
        panel = []
        for environment in ENVIRONMENTS:
            values = grouped[(model, target, environment)]
            panel.append(
                {
                    "source_id": SOURCE_ID,
                    "panel_id": panel_id,
                    "target": target,
                    "downstream_model": model.split("-", 1)[0],
                    "environment": environment,
                    "pre_outcome_measurements": {
                        **ENVIRONMENTS[environment],
                        "initial_training_count": 1000,
                        "acquired_count": 954,
                        "final_training_count": 1954,
                    },
                    "outcome": {
                        "mean_test_r2": statistics.fmean(values),
                        "test_r2_standard_deviation": statistics.stdev(values),
                        "independent_model_fits": len(values),
                    },
                }
            )
        utilities = [arm["outcome"]["mean_test_r2"] for arm in panel]
        low, high = min(utilities), max(utilities)
        for arm, utility in zip(panel, utilities):
            normalized = 0.5 if high == low else (utility - low) / (high - low)
            arm["derived"] = {
                "native_utility": utility,
                "panel_normalized_utility": normalized,
                "panel_normalized_regret": 1.0 - normalized,
            }
        arms.extend(panel)

    return {
        "artifact": "zhang_2023_etal_panels_v1",
        "source_id": SOURCE_ID,
        "source_revision": REVISION,
        "panel_count": len(models),
        "arm_count": len(arms),
        "primary_outcome": "mean held-out R2 across 30 released downstream-model fits",
        "normalization": "test R2 min-max normalized within target and downstream model",
        "matched_contract": {
            "test_count": 4898,
            "initial_training_count": 1000,
            "acquired_count": 954,
            "final_training_count": 1954,
            "independent_model_fits": 30,
        },
        "source_files": {
            "results/ML_r2.csv": {"sha256": RESULT_SHA256},
            "results/info_entropy_evolution.csv": {"sha256": ENTROPY_SHA256},
        },
        "interpretation_boundary": [
            "The release contains exact 30-fit histories for random forest and gradient boosting; other model families shown in the paper are not reconstructed from figures.",
            "Bulk and shear modulus are repeated target views of one pair of selected training sets.",
            "ET-AL uses formation-energy entropy to target underrepresented structure space before the downstream modulus models are fit.",
        ],
        "arms": arms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = ingest(args.repository)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
