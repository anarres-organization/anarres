#!/usr/bin/env python3
"""Integrity checks for the retrospective finance regression-risk audit."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "scripts" / "analyze_regression_risk.py"
RESULT = HERE / "results" / "regression_risk_summary.json"


def load_analyzer():
    specification = importlib.util.spec_from_file_location("finance_regression_risk", SCRIPT)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_released_result_matches_analysis() -> None:
    analyzer = load_analyzer()
    expected = json.loads(RESULT.read_text(encoding="utf-8"))
    observed = analyzer.analyze()
    assert observed == expected
    assert observed["support"] == {
        "admitted_panels": 44,
        "contrasts": 165,
        "regressions": 105,
        "sources": 8,
    }
    practical = observed["rules"]["practical_rule"]
    volume = observed["rules"]["more_data"]
    assert practical["source_macro_roc_auc"] == 0.815183
    assert practical["source_macro_roc_auc"] > volume["source_macro_roc_auc"]


if __name__ == "__main__":
    test_released_result_matches_analysis()
