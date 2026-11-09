#!/usr/bin/env python3
"""Summarize the frozen checkpoint-qualification panel and apply its gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path


PRACTICAL_EQUIVALENCE = 0.05
MINIMUM_SUCCESSES = 15


def summarize_backend(directory: Path, expected_ids: list[str]) -> dict:
    rows = []
    failures = []
    for material_id in expected_ids:
        path = directory / f"{material_id}.json"
        if not path.exists():
            failures.append(material_id)
            continue
        row = json.loads(path.read_text(encoding="utf-8"))
        if not row["relaxation"]["converged"]:
            failures.append(material_id)
            continue
        rows.append(row)
    maes = [row["metrics"]["frequency_mae_thz"] for row in rows]
    rmses = [row["metrics"]["frequency_rmse_thz"] for row in rows]
    times = [
        row["timing_seconds"]["total"] - row["timing_seconds"]["model_load"]
        for row in rows
    ]
    stability = [
        row["metrics"]["reference_stable"] == row["metrics"]["predicted_stable"]
        for row in rows
    ]
    return {
        "successes": len(rows),
        "failures": failures,
        "eligible": len(rows) >= MINIMUM_SUCCESSES,
        "frequency_mae_thz": {
            "mean": statistics.fmean(maes) if maes else None,
            "median": statistics.median(maes) if maes else None,
        },
        "frequency_rmse_thz": {
            "mean": statistics.fmean(rmses) if rmses else None,
            "median": statistics.median(rmses) if rmses else None,
        },
        "stability_accuracy": statistics.fmean(stability) if stability else None,
        "evaluation_runtime_excluding_model_load_seconds": {
            "mean": statistics.fmean(times) if times else None,
            "median": statistics.median(times) if times else None,
        },
        "model_sha256": sorted({row["model_sha256"] for row in rows}),
    }


def select_backend(summaries: dict[str, dict]) -> tuple[str, str]:
    eligible = {name: result for name, result in summaries.items() if result["eligible"]}
    if not eligible:
        return "none", "No checkpoint passed the minimum-success gate."
    if len(eligible) == 1:
        selected = next(iter(eligible))
        return selected, "Only one checkpoint passed the minimum-success gate."

    ordered = sorted(eligible, key=lambda name: eligible[name]["frequency_mae_thz"]["mean"])
    best, runner_up = ordered[:2]
    best_mae = eligible[best]["frequency_mae_thz"]["mean"]
    runner_mae = eligible[runner_up]["frequency_mae_thz"]["mean"]
    relative_gap = (runner_mae - best_mae) / runner_mae
    if relative_gap > PRACTICAL_EQUIVALENCE:
        return best, "Selected by lower mean phonon-frequency MAE."

    stability_order = sorted(
        eligible,
        key=lambda name: (
            -eligible[name]["stability_accuracy"],
            eligible[name]["evaluation_runtime_excluding_model_load_seconds"]["median"],
        ),
    )
    return stability_order[0], (
        "Mean frequency MAE was within the five-percent equivalence band; selected by stability "
        "accuracy and then median runtime."
    )


def summarize(roles_path: Path, results_root: Path) -> dict:
    roles = json.loads(roles_path.read_text(encoding="utf-8"))
    ids = roles["roles"]["checkpoint_qualification"]
    summaries = {
        backend: summarize_backend(results_root / backend, ids)
        for backend in ("mace", "nequix")
    }
    selected, rationale = select_backend(summaries)
    return {
        "artifact": "anarres_mlip_checkpoint_qualification_v1",
        "status": "complete" if selected != "none" else "failed",
        "panel": {
            "role_manifest_sha256": hashlib.sha256(roles_path.read_bytes()).hexdigest(),
            "materials": len(ids),
            "material_ids": ids,
        },
        "gate": {
            "minimum_successes": MINIMUM_SUCCESSES,
            "primary_metric": "mean commensurate-phonon frequency MAE in THz",
            "practical_equivalence_relative": PRACTICAL_EQUIVALENCE,
            "tie_breakers": [
                "stability accuracy",
                "median evaluation runtime excluding model load",
            ],
        },
        "checkpoints": summaries,
        "selected_backend": selected,
        "selection_rationale": rationale,
        "interpretation": (
            "This gate selects a common starting checkpoint. It contains no candidate-environment "
            "post-training outcome and does not estimate environment utility."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--roles", type=Path, required=True)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.roles, args.results_root)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
