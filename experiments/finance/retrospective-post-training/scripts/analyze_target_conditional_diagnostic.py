#!/usr/bin/env python3
"""Test a derived alignment/interference coordinate without replacing v2."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "scripts" / "analyze_expanded_bridge.py"
OUT = ROOT / "results" / "target_conditional_diagnostic.json"

INTERVENTION_FEATURES = [
    "data_volume",
    "quality_control",
    "retention_control",
    "verifier_alignment",
    "policy_relative_selection",
    "domain_specific_selection",
    "transcript_refinement",
    "qa_refinement",
    "feedback_locality",
    "efficient_rollout",
    "curriculum_progression",
    "target_alignment",
    "source_diversity",
    "human_labeled_fraction",
]


def load_v2():
    spec = importlib.util.spec_from_file_location("finance_bridge_v2", V2)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def derived(row: dict) -> tuple[float, float, float, float]:
    values = row["feature_values"]
    aligned_values = [
        values[name]
        for name in ("target_alignment", "verifier_alignment")
        if values[f"{name}__observed"]
    ]
    aligned = max(aligned_values) if aligned_values else 0.0
    observed = 1.0 if aligned_values else 0.0
    exposure = max(
        [values[name] for name in INTERVENTION_FEATURES if values[f"{name}__observed"]] + [0.0]
    )
    retention = values["retention_control"] if values["retention_control__observed"] else 0.0
    interference = exposure * (1.0 - aligned) * (1.0 - retention) if observed else 0.0
    return aligned, observed, interference, observed


def main() -> None:
    bridge = load_v2()
    rows = bridge.all_rows()
    predictions = {name: {} for name in ("v2_rule", "derived_rule", "v2_ridge", "derived_ridge")}
    for held_out in sorted({row["source"] for row in rows}):
        train = [row for row in rows if row["source"] != held_out]
        test = [row for row in rows if row["source"] == held_out]
        v2_coef = bridge.ridge_fit([row["x"] for row in train], [row["utility"] for row in train])
        derived_coef = bridge.ridge_fit(
            [row["x"] + list(derived(row)) for row in train],
            [row["utility"] for row in train],
        )
        for row in test:
            key = bridge.row_key(row)
            aligned, _, interference, _ = derived(row)
            predictions["v2_rule"][key] = bridge.practical_value(row)
            predictions["derived_rule"][key] = (
                bridge.practical_value(row) + 0.5 * aligned - 0.5 * interference
            )
            predictions["v2_ridge"][key] = bridge.predict(v2_coef, row["x"])
            predictions["derived_ridge"][key] = bridge.predict(
                derived_coef, row["x"] + list(derived(row))
            )

    output = {
        "schema_version": 1,
        "status": "RETROSPECTIVE_DIAGNOSTIC__NOT_PROMOTED",
        "support": {
            "sources": len({row["source"] for row in rows}),
            "panels": len({(row["source"], row["panel"]) for row in rows}),
            "arms": len(rows),
        },
        "evaluations": {
            name: bridge.score(rows, values)["source_macro"] for name, values in predictions.items()
        },
        "decision": (
            "Do not add a broad target-family interference coordinate to the fitted bridge. "
            "It does not improve source-held-out ordering or regret. Re-encode alignment and "
            "interference at the task level before another fitted model is attempted."
        ),
    }
    OUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
