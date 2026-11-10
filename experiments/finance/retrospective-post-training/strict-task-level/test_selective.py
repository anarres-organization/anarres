#!/usr/bin/env python3
"""Integrity checks for source-held-out selective finance predictions."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "score_selective.py"
RESULT = HERE / "SELECTIVE_SCORE.json"


def load_score():
    specification = importlib.util.spec_from_file_location("finance_selective", SCRIPT)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_released_score_matches_analysis() -> None:
    scorer = load_score()
    released = json.loads(RESULT.read_text(encoding="utf-8"))
    observed = scorer.analyze()
    assert observed == released
    assert observed["support"]["candidate_pairs"] == 309

    practical = observed["rules"]["practical_rule"]
    selective = practical["operating_points"]["target_0.85"]
    assert practical["unfiltered_pairwise_accuracy"] == 0.815534
    assert selective["decided_pairs"] == 235
    assert selective["coverage"] == 0.760518
    assert selective["selective_pairwise_accuracy"] == 0.904255
    assert selective["source_macro_selective_accuracy"] == 0.895817
    assert selective["sources_with_decisions"] == 7
    assert observed["method"]["heldout_outcomes_used_for_threshold"] is False

    volume = observed["rules"]["more_data"]["operating_points"]["target_0.85"]
    assert selective["selective_pairwise_accuracy"] > volume["selective_pairwise_accuracy"]


if __name__ == "__main__":
    test_released_score_matches_analysis()
