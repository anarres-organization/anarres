#!/usr/bin/env python3
"""Summarize the frozen learning-rate qualification from reloaded checkpoints."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

GRADIENT_PATTERN = re.compile(r"['\"]train/grad_norm['\"]:\s*([^,}\s]+)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def compact_evaluation(path: Path) -> dict:
    evaluation = json.loads(path.read_text(encoding="utf-8"))
    metrics = evaluation["metrics"]
    if not metrics or not all(math.isfinite(float(value)) for value in metrics.values()):
        raise ValueError(f"non-finite evaluation metrics: {path}")
    return {
        "artifact_sha256": sha256(path),
        "dataset_sha256": evaluation["dataset_sha256"],
        "model_sha256": evaluation["model_sha256"],
        "records": evaluation["records"],
        "split": evaluation["split"],
        "loss_contract": evaluation["loss_contract"],
        "metrics": {key: float(value) for key, value in metrics.items()},
    }


def gradient_summary(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    values = [float(match) for match in GRADIENT_PATTERN.findall(text)]
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError(f"training log has no finite gradient norms: {path}")
    return {
        "artifact_sha256": sha256(path),
        "observations": len(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def learning_rate_label(learning_rate: float) -> str:
    return f"lr_{learning_rate:.0e}".replace("e-0", "e-").replace("e+0", "e+")


def summarize(protocol_path: Path, baseline_path: Path, run_root: Path) -> dict:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    baseline = compact_evaluation(baseline_path)
    baseline_loss = baseline["metrics"]["loss"]
    runs = []
    for learning_rate in protocol["qualification_grid"]["learning_rates"]:
        label = learning_rate_label(learning_rate)
        run_dir = run_root / label
        evaluation = compact_evaluation(run_dir / "reloaded_efs.json")
        checkpoint = run_dir / "checkpoints" / "epoch_0001.nqx"
        gradients = gradient_summary(run_dir / "train_rerun.log")
        same_contract = all(
            evaluation[key] == baseline[key]
            for key in ("dataset_sha256", "records", "split", "loss_contract")
        )
        loss = evaluation["metrics"]["loss"]
        passed = same_contract and loss <= baseline_loss
        runs.append(
            {
                "learning_rate": learning_rate,
                "passed": passed,
                "heldout_loss": loss,
                "relative_loss_change": loss / baseline_loss - 1.0,
                "force_mae": evaluation["metrics"]["force_mae"],
                "stress_mae_per_atom": evaluation["metrics"]["stress_mae_per_atom"],
                "checkpoint_sha256": sha256(checkpoint),
                "evaluation": evaluation,
                "gradient_norm": gradients,
            }
        )
    passing = [run for run in runs if run["passed"]]
    if not passing:
        raise ValueError("no qualification run satisfies the frozen selection rule")
    selected = max(passing, key=lambda run: (run["learning_rate"], -run["heldout_loss"]))
    return {
        "artifact": "anarres_mlip_training_qualification_result_v1",
        "status": "complete_before_final_candidate_training",
        "protocol_sha256": sha256(protocol_path),
        "qualification_environment": protocol["qualification_environment"],
        "starting_checkpoint": protocol["starting_checkpoint"],
        "baseline": baseline,
        "runs": runs,
        "selection_rule": protocol["qualification_grid"]["selection_rule"],
        "selected_learning_rate": selected["learning_rate"],
        "selected_checkpoint_sha256": selected["checkpoint_sha256"],
        "outcome_boundary": {
            "phonon_target_outcomes_used": False,
            "final_candidate_training_outcomes_used": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.protocol, args.baseline, args.run_root)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
