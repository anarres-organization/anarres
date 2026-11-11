#!/usr/bin/env python3
"""Integrity checks for the LongFinanceQA component score."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def test_score() -> None:
    subprocess.run([sys.executable, str(HERE / "score_holdout.py")], check=True)
    score = json.loads((HERE / "SCORE.json").read_text(encoding="utf-8"))
    assert score["source_level_tests"] == 1
    assert score["directional_correct"] == 24
    assert score["directional_scored"] == 25
    assert score["directional_accuracy"] == 0.96
    assert score["prediction_families_supported"] == 4
    assert score["prediction_families_scored"] == 4
    assert len(score["unscored_predictions"]) == 2


if __name__ == "__main__":
    test_score()
