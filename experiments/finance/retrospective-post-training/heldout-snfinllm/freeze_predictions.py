#!/usr/bin/env python3
"""Freeze SNFinLLM rankings without loading its reported outcomes."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ANALYSIS = ROOT / "scripts" / "analyze_expanded_bridge.py"
CANDIDATES = HERE / "CANDIDATES.json"
OUTPUT = HERE / "PREDICTIONS.json"
HASH = HERE / "PREDICTIONS.sha256"


def load_analysis():
    spec = importlib.util.spec_from_file_location("finance_bridge", ANALYSIS)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main(output: Path = OUTPUT, hash_path: Path = HASH) -> None:
    bridge = load_analysis()
    candidates = json.loads(CANDIDATES.read_text())
    panel = {
        "source_id": "snfinllm_2024_holdout",
        "panel_id": "snfinllm_stage_candidates",
        "model": "held_out",
        "target": "held_out",
        "arms": [
            {"id": arm["id"], "score": 0.0, "treatment": arm["treatment"]}
            for arm in candidates["arms"]
        ],
    }
    candidate_rows = bridge.mapped_recovered_panel(panel)
    training_rows = bridge.all_rows()
    full_coef = bridge.ridge_fit(
        [row["x"] for row in training_rows], [row["utility"] for row in training_rows]
    )
    compact_coef = bridge.ridge_fit(
        [bridge.compact_x(row) for row in training_rows],
        [row["utility"] for row in training_rows],
    )

    predictions = {}
    for row in candidate_rows:
        predictions[row["arm"]] = {
            "practical_rule": bridge.practical_value(row),
            "full_ridge": bridge.predict(full_coef, row["x"]),
            "compact_ridge": bridge.predict(compact_coef, bridge.compact_x(row)),
            "more_data": row["feature_values"]["data_volume"],
            "feature_values": row["feature_values"],
        }

    ranking_tiers = {}
    for method in ("practical_rule", "full_ridge", "compact_ridge", "more_data"):
        scores = sorted({predictions[arm][method] for arm in predictions}, reverse=True)
        ranking_tiers[method] = [
            sorted(arm for arm in predictions if predictions[arm][method] == score)
            for score in scores
        ]
    record = {
        "schema_version": 1,
        "status": "FROZEN_BEFORE_OUTCOME_EXTRACTION",
        "representation_commit": json.loads((HERE / "FREEZE.json").read_text())["representation"][
            "git_commit"
        ],
        "candidate_file_sha256": hashlib.sha256(CANDIDATES.read_bytes()).hexdigest(),
        "predictions": predictions,
        "ranking_tiers": ranking_tiers,
        "interpretation": (
            "Rankings apply wherever the paper reports comparable outcomes for these stages. "
            "A tie remains a tie and receives fractional decision credit."
        ),
    }
    serialized = json.dumps(record, indent=2, sort_keys=True) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    hash_path.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(serialized)
    hash_path.write_text(f"{hashlib.sha256(serialized.encode()).hexdigest()}  {output.name}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--hash-output", type=Path, default=HASH)
    arguments = parser.parse_args()
    main(arguments.output, arguments.hash_output)
