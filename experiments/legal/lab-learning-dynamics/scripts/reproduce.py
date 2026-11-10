#!/usr/bin/env python3
"""Reconstruct the compact LAB learning-dynamics and risk summary."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ROOT / "results" / "summary.json"


def canonical_json(value: dict[str, object]) -> str:
    """Serialize one released artifact in its byte-stable form."""
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def compute() -> dict[str, object]:
    checkpoints = json.loads((ROOT / "data" / "checkpoints.json").read_text())
    risk = json.loads((ROOT / "data" / "regression-risk.json").read_text())
    base = checkpoints[0]
    best = max(checkpoints, key=lambda row: row["criterion_pass_rate"])
    final = checkpoints[-1]
    metrics = risk["metrics"]
    return {
        "checkpoint_count": len(checkpoints),
        "base_step": base["step"],
        "base_criterion_pass_percent": round(100 * base["criterion_pass_rate"], 6),
        "best_step": best["step"],
        "best_criterion_pass_percent": round(100 * best["criterion_pass_rate"], 6),
        "final_step": final["step"],
        "final_criterion_pass_percent": round(100 * final["criterion_pass_rate"], 6),
        "severe_regressions": risk["support"]["severe_regressions"],
        "static_auc": metrics["static"]["roc_auc"],
        "behavior_auc": metrics["behavior"]["roc_auc"],
        "combined_auc": metrics["combined"]["roc_auc"],
        "static_beats_random_ap": metrics["static"]["average_precision"]
        > metrics["random_fingerprint"]["average_precision"],
        "static_beats_shuffled_ap": metrics["static"]["average_precision"]
        > metrics["shuffled_static_pairing"]["average_precision"],
    }


if __name__ == "__main__":
    observed = compute()
    serialized = canonical_json(observed)
    if serialized != EXPECTED.read_text():
        raise SystemExit("recomputed LAB summary does not byte-match the released result")
    print(serialized, end="")
