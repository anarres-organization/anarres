#!/usr/bin/env python3
"""Integrity checks for the FinToolSyn excluded-source score."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def test_score() -> None:
    subprocess.run([sys.executable, str(HERE / "score_holdout.py")], check=True)
    score = json.loads((HERE / "SCORE.json").read_text(encoding="utf-8"))
    assert score["directional_correct"] == 9
    assert score["directional_scored"] == 9
    assert score["directional_accuracy"] == 1.0
    assert score["best_candidate_correct"] == 2
    assert score["best_candidate_scored"] == 2
    assert score["regression_correct"] == 3
    assert score["regression_scored"] == 3
    assert len(score["abstentions"]) == 1


if __name__ == "__main__":
    test_score()
