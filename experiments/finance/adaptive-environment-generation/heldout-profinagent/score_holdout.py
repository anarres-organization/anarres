#!/usr/bin/env python3
"""Score frozen ProFinAgent component predictions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PREDICTIONS = ROOT / "PREDICTIONS.json"
OUTCOMES = ROOT / "OUTCOMES.json"
SCORE = ROOT / "SCORE.json"
MANIFEST = ROOT / "MANIFEST.sha256.json"


def main() -> None:
    predictions = json.loads(PREDICTIONS.read_text())["predictions"]
    outcomes = json.loads(OUTCOMES.read_text())
    cells = outcomes["accuracy_cells"]

    full_over_dag = [cell["full"] > cell["dag_only"] for cell in cells]
    full_over_cbm = [cell["full"] > cell["cbm_only"] for cell in cells]
    latency = outcomes["latency_seconds"]
    dag_faster = latency["dag"] < latency["sequential"]

    gains = {
        level: sum(cell["tool_use"] - cell["baseline"] for cell in cells if cell["level"] == level)
        / sum(cell["level"] == level for cell in cells)
        for level in ("L1", "L2", "L3")
    }
    computation_gain_exceeds_retrieval = max(gains["L2"], gains["L3"]) > gains["L1"]
    full_not_uniformly_best = any(
        cell["full"] < max(cell["baseline"], cell["tool_use"], cell["dag_only"], cell["cbm_only"])
        for cell in cells
    )

    correctness = {
        "full_over_no_memory_accuracy": all(full_over_dag),
        "full_over_no_dag_accuracy": all(full_over_cbm),
        "dag_over_sequential_latency": dag_faster,
        "tools_largest_on_procedural_computation": computation_gain_exceeds_retrieval,
        "full_system_not_uniformly_best": full_not_uniformly_best,
    }
    ordered_ids = [prediction["id"] for prediction in predictions]
    if set(ordered_ids) != set(correctness):
        raise ValueError("prediction and scoring identities differ")

    output = {
        "schema_version": 1,
        "holdout_id": "profinagent_component_holdout_v1",
        "status": "SCORED_AFTER_FREEZE",
        "prediction_families_correct": sum(correctness.values()),
        "prediction_families_total": len(correctness),
        "prediction_family_accuracy": sum(correctness.values()) / len(correctness),
        "atomic_directional_checks": {
            "correct": sum(full_over_dag) + sum(full_over_cbm) + int(dag_faster),
            "total": len(full_over_dag) + len(full_over_cbm) + 1,
        },
        "tool_use_gain_by_level_percentage_points": {
            level: round(value, 4) for level, value in gains.items()
        },
        "accuracy_component_checks": {
            "full_over_dag_only": {"correct": sum(full_over_dag), "total": len(full_over_dag)},
            "full_over_cbm_only": {"correct": sum(full_over_cbm), "total": len(full_over_cbm)},
        },
        "latency_check": {
            "sequential_seconds": latency["sequential"],
            "dag_seconds": latency["dag"],
            "reported_reduction": latency["reported_reduction"],
            "correct": dag_faster,
        },
        "predictions": [
            {"id": prediction_id, "correct": correctness[prediction_id]}
            for prediction_id in ordered_ids
        ],
        "interpretation": [
            "component-level predictions were frozen before Table 5 and Figure 4 were extracted",
            "the paper abstract already disclosed aggregate ProFinAgent and latency gains",
            "the holdout therefore scores component directions rather than the "
            "disclosed aggregate comparison",
            "the failed tool-gradient and uniform-dominance predictions remain unchanged",
        ],
    }
    SCORE.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    files = {
        "CONTRACT.json": ROOT / "CONTRACT.json",
        "FREEZE_MANIFEST.sha256.json": ROOT / "FREEZE_MANIFEST.sha256.json",
        "OUTCOMES.json": OUTCOMES,
        "PREDICTIONS.json": PREDICTIONS,
        "README.md": ROOT / "README.md",
        "SCORE.json": SCORE,
        "SOURCE.json": ROOT / "SOURCE.json",
        "score_holdout.py": Path(__file__),
    }
    manifest = {
        label: hashlib.sha256(path.read_bytes()).hexdigest() for label, path in files.items()
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
