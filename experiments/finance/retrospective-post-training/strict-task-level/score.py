#!/usr/bin/env python3
"""Score the strict task-level finance bridge."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ANALYSIS = ROOT / "scripts" / "analyze_expanded_bridge.py"
DATA = ROOT / "data" / "recovered_panels.json"
OUT = HERE / "SCORE.json"
MANIFEST = HERE / "MANIFEST.sha256.json"


def load_analysis():
    spec = importlib.util.spec_from_file_location("finance_bridge", ANALYSIS)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def admitted_rows(bridge) -> list[dict]:
    document = json.loads(DATA.read_text())
    rows = []
    for panel in document["panels"]:
        mapped = bridge.mapped_recovered_panel(panel)
        if not mapped:
            continue
        if any(row["model"] == "unreported" or row["target"] == "unreported" for row in mapped):
            continue
        if not all(row["feature_values"]["target_alignment__observed"] for row in mapped):
            continue
        rows.extend(mapped)
    return rows


def support(rows: list[dict]) -> dict:
    return {
        "sources": len({row["source"] for row in rows}),
        "panels": len({(row["source"], row["panel"]) for row in rows}),
        "arms": len(rows),
        "models": len({(row["source"], row["model"]) for row in rows}),
        "targets": len({(row["source"], row["target"]) for row in rows}),
    }


def main() -> None:
    bridge = load_analysis()
    rows = admitted_rows(bridge)
    evaluations = {}
    for held_out in ("source", "model", "target"):
        predictions = bridge.grouped_predictions(rows, held_out)
        evaluations[f"leave_one_{held_out}_out"] = {
            name: bridge.score(rows, values) for name, values in predictions.items()
        }

    source_result = evaluations["leave_one_source_out"]
    output = {
        "schema_version": 1,
        "status": "RETROSPECTIVE_STRICT_TASK_LEVEL",
        "admission": {
            "every_arm_has_explicit_target_alignment": True,
            "model_and_target_are_identified": True,
            "outcomes_do_not_enter_admission_or_features": True,
        },
        "support": support(rows),
        "sources": sorted({row["source"] for row in rows}),
        "evaluations": evaluations,
        "paired_source_comparison": bridge.paired_source_comparison(
            source_result, "practical_rule", "more_data"
        ),
        "guardrails": [
            "all outcomes were public before this retrospective audit",
            "the practical rule and its weights predate this strict subset",
            "source-native outcomes are normalized only within decision panels",
            "model, source, target, method names, and outcomes are excluded from features",
        ],
    }
    OUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    paths = [ROOT / "FEATURE_MAPPING.md", DATA, ANALYSIS, Path(__file__), OUT]
    manifest = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
