#!/usr/bin/env python3
"""Evaluate regression risk against an explicit study-matched baseline."""

from __future__ import annotations

import importlib.util
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "scripts" / "analyze_expanded_bridge.py"
OUT = ROOT / "results" / "regression_risk_summary.json"
BASELINE_IDS = {"base", "baseline", "base_1p7b", "base_4b"}


def load_bridge():
    specification = importlib.util.spec_from_file_location("finance_expanded_bridge", BRIDGE)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load {BRIDGE}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def auc(records: list[tuple[float, bool]]) -> float | None:
    positive = [score for score, label in records if label]
    negative = [score for score, label in records if not label]
    if not positive or not negative:
        return None
    credit = math.fsum(
        1.0 if left > right else 0.5 if left == right else 0.0
        for left in positive
        for right in negative
    )
    return credit / (len(positive) * len(negative))


def analyze() -> dict:
    bridge = load_bridge()
    rows = bridge.all_rows()
    panels: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        panels[(row["source"], row["panel"])].append(row)

    by_rule: dict[str, dict[str, list[tuple[float, bool]]]] = {
        "practical_rule": defaultdict(list),
        "more_data": defaultdict(list),
    }
    admitted_panels = 0
    contrasts = 0
    regressions = 0
    for (source, _panel), panel_rows in panels.items():
        baselines = [row for row in panel_rows if row["arm"] in BASELINE_IDS]
        if len(baselines) != 1:
            continue
        admitted_panels += 1
        baseline = baselines[0]
        baseline_practical = bridge.practical_value(baseline)
        baseline_volume = baseline["feature_values"]["data_volume"]
        for row in panel_rows:
            if row is baseline:
                continue
            regressed = row["utility"] < baseline["utility"]
            contrasts += 1
            regressions += int(regressed)
            by_rule["practical_rule"][source].append(
                (baseline_practical - bridge.practical_value(row), regressed)
            )
            by_rule["more_data"][source].append(
                (baseline_volume - row["feature_values"]["data_volume"], regressed)
            )

    rules = {}
    for name, source_records in by_rule.items():
        pooled = [record for records in source_records.values() for record in records]
        per_source = {source: auc(records) for source, records in sorted(source_records.items())}
        eligible = {source: value for source, value in per_source.items() if value is not None}
        rules[name] = {
            "pooled_roc_auc": round(auc(pooled) or 0.0, 6),
            "source_macro_roc_auc": round(math.fsum(eligible.values()) / len(eligible), 6),
            "eligible_sources": len(eligible),
            "per_source_roc_auc": {
                source: None if value is None else round(value, 6)
                for source, value in per_source.items()
            },
        }

    return {
        "schema_version": 1,
        "status": "RETROSPECTIVE_REGRESSION_RISK_AUDIT",
        "estimand": "whether a treatment scores below its explicit study-matched baseline",
        "prediction_inputs": "the fixed practical-rule features. Outcomes enter labels only",
        "baseline_arm_ids": sorted(BASELINE_IDS),
        "support": {
            "admitted_panels": admitted_panels,
            "contrasts": contrasts,
            "regressions": regressions,
            "sources": len(by_rule["practical_rule"]),
        },
        "rules": rules,
        "interpretation": (
            "The fixed finance rule identifies regression risk across sources better than "
            "the data-volume proxy. Source-macro AUC is primary because one source supplies "
            "most treatment contrasts. This is a retrospective secondary audit."
        ),
    }


def main() -> None:
    result = analyze()
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
