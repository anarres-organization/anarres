#!/usr/bin/env python3
"""Validate and compact starting-checkpoint phonon measurements."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def summarize(roles_path: Path, results_dir: Path, model_sha256: str) -> dict:
    roles = json.loads(roles_path.read_text(encoding="utf-8"))
    workflow = None
    rows = []
    expected = []
    for role in ("development", "prospective"):
        expected.extend((role, material_id) for material_id in roles["roles"][role])
    for role, material_id in expected:
        path = results_dir / f"{material_id}.json"
        result = json.loads(path.read_text(encoding="utf-8"))
        if result["material_id"] != material_id or result["model_sha256"] != model_sha256:
            raise ValueError(f"identity mismatch: {path}")
        if result["backend"] != "nequix":
            raise ValueError(f"unexpected backend: {path}")
        if workflow is None:
            workflow = result["workflow"]
        elif result["workflow"] != workflow:
            raise ValueError(f"workflow mismatch: {path}")
        metrics = result["metrics"]
        numeric = (
            "frequency_mae_thz",
            "frequency_rmse_thz",
            "maximum_frequency_error_thz",
            "reference_stability_margin_kelvin",
            "predicted_stability_margin_kelvin",
        )
        if not all(math.isfinite(float(metrics[key])) for key in numeric):
            raise ValueError(f"non-finite target metric: {path}")
        rows.append(
            {
                "material_id": material_id,
                "role": role,
                "frequency_mae_thz": metrics["frequency_mae_thz"],
                "frequency_rmse_thz": metrics["frequency_rmse_thz"],
                "reference_stable": metrics["reference_stable"],
                "predicted_stable": metrics["predicted_stable"],
                "reference_stability_margin_kelvin": metrics["reference_stability_margin_kelvin"],
                "predicted_stability_margin_kelvin": metrics["predicted_stability_margin_kelvin"],
                "relaxation_converged": result["relaxation"]["converged"],
                "source_artifact_sha256": sha256(path),
            }
        )
    observed = {path.stem for path in results_dir.glob("*.json")}
    expected_ids = {material_id for _, material_id in expected}
    if observed != expected_ids:
        raise ValueError("result directory contains missing or unexpected target identities")
    return {
        "artifact": "anarres_mlip_starting_checkpoint_targets_v1",
        "status": "complete_before_candidate_training",
        "target_roles_sha256": sha256(roles_path),
        "role_hashes": {key: roles["role_hashes"][key] for key in ("development", "prospective")},
        "model_sha256": model_sha256,
        "workflow": workflow,
        "counts": {
            "development": len(roles["roles"]["development"]),
            "prospective": len(roles["roles"]["prospective"]),
        },
        "targets": rows,
        "outcome_boundary": {
            "measurements_are_starting_checkpoint_features": True,
            "candidate_training_outcomes_used": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-roles", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--model-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.target_roles, args.results_dir, args.model_sha256)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
