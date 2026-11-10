#!/usr/bin/env python3
"""Recompute the expanded bridge with no-training alignment controls corrected."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "scripts" / "analyze_expanded_bridge.py"
REPRODUCER = ROOT / "scripts" / "reproduce_expanded_bridge.py"
OUT = ROOT / "results" / "expanded_summary_corrected.json"
MANIFEST = ROOT / "results" / "EXPANDED_CORRECTED_MANIFEST.sha256.json"


def load_v2():
    specification = importlib.util.spec_from_file_location("finance_bridge_reproducer", REPRODUCER)
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    return module.load_bridge()


def corrected_rows(bridge) -> list[dict]:
    initial = json.loads(bridge.INITIAL.read_text())
    rows = []
    for panel in initial["panels"]:
        scores = [arm["score"] for arm in panel["arms"]]
        low, high = min(scores), max(scores)
        for arm in panel["arms"]:
            old = dict(zip(initial["feature_names"], arm["features"], strict=True))
            values = bridge.empty_features()
            bridge.observed_feature(values, "quality_control", old["quality_control"])
            bridge.observed_feature(values, "retention_control", old["retention_control"])
            bridge.observed_feature(values, "verifier_alignment", old["verifier_alignment"])
            bridge.observed_feature(
                values, "policy_relative_selection", old["policy_relative_difficulty"]
            )
            active_training = float(
                bool(
                    old["sft_stage"]
                    or old["rl_stage"]
                    or old["raw_volume_only"]
                    or old["data_fraction"] > 0
                )
            )
            bridge.observed_feature(
                values,
                "target_alignment",
                active_training * (1.0 - old["out_of_domain_mix"]),
            )
            bridge.observed_feature(values, "data_volume", old["data_fraction"])
            rows.append(
                bridge.make_row(
                    panel["study_id"],
                    panel["panel_id"],
                    arm["id"],
                    "unreported",
                    "unreported",
                    arm["score"],
                    low,
                    high,
                    values,
                )
            )
    recovered = json.loads(bridge.RECOVERED.read_text())
    for panel in recovered["panels"]:
        rows.extend(bridge.mapped_recovered_panel(panel))
    return rows


def main() -> None:
    bridge = load_v2()
    rows = corrected_rows(bridge)
    evaluations = {}
    for group_key in ("source", "model", "target"):
        predictions = bridge.grouped_predictions(rows, group_key)
        evaluations[f"leave_one_{group_key}_out"] = {
            name: bridge.score(rows, values) for name, values in predictions.items()
        }
    source_result = evaluations["leave_one_source_out"]
    rank_rows = bridge.rank_normalized_rows(rows)
    rank_predictions = bridge.grouped_predictions(rank_rows, "source")
    rank_sensitivity = {
        name: bridge.score(rank_rows, values) for name, values in rank_predictions.items()
    }
    panels_per_source: dict[str, set[str]] = {}
    for row in rows:
        panels_per_source.setdefault(row["source"], set()).add(row["panel"])
    multi_panel_rows = [row for row in rows if len(panels_per_source[row["source"]]) >= 2]
    multi_panel_predictions = bridge.grouped_predictions(multi_panel_rows, "source")
    multi_panel_sensitivity = {
        "support": {
            "sources": len({row["source"] for row in multi_panel_rows}),
            "panels": len({(row["source"], row["panel"]) for row in multi_panel_rows}),
            "arms": len(multi_panel_rows),
        },
        "evaluations": {
            name: bridge.score(multi_panel_rows, values)
            for name, values in multi_panel_predictions.items()
        },
    }
    multi_panel_sensitivity["paired_source_comparison"] = bridge.paired_source_comparison(
        multi_panel_sensitivity["evaluations"], "practical_rule", "more_data"
    )
    output = {
        "schema_version": 1,
        "status": "RETROSPECTIVE_SOURCE_RECOVERED__CONTROL_ALIGNMENT_CORRECTED",
        "correction": (
            "No-training controls in the four initial studies receive target alignment zero. "
            "The earlier conversion assigned one because zero out-of-domain mixture was "
            "interpreted without conditioning on whether a training intervention existed."
        ),
        "support": {
            "sources": len({row["source"] for row in rows}),
            "panels": len({(row["source"], row["panel"]) for row in rows}),
            "arms": len(rows),
        },
        "evaluations": evaluations,
        "rank_utility_sensitivity": rank_sensitivity,
        "multi_panel_source_sensitivity": multi_panel_sensitivity,
        "paired_source_comparison": bridge.paired_source_comparison(
            source_result, "practical_rule", "more_data"
        ),
        "publication_cutoff_sensitivity": bridge.temporal_cutoff_audit(rows),
        "source_exclusion_sensitivity": bridge.source_exclusion_audit(rows),
        "practical_feature_ablation": bridge.practical_feature_ablation(rows),
        "ridge_penalty_sensitivity": bridge.ridge_penalty_audit(rows),
        "shuffled_pairing_control": bridge.shuffled_control(rows),
        "guardrails": [
            "the earlier frozen source-holdout predictions remain unchanged",
            "this correction was applied after both source-level holdouts were scored",
            "all outcomes remain retrospective and public",
        ],
    }
    OUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    paths = [
        ROOT / "FEATURE_MAPPING.md",
        ROOT / "SOURCES.json",
        bridge.INITIAL,
        bridge.RECOVERED,
        V2,
        REPRODUCER,
        Path(__file__),
        OUT,
    ]
    manifest = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
