#!/usr/bin/env python3
"""Integrity checks for the CDF-GC excluded-source score."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def test_score() -> None:
    subprocess.run([sys.executable, str(HERE / "score_holdout.py")], check=True)
    score = json.loads((HERE / "SCORE.json").read_text(encoding="utf-8"))
    assert score["directional_correct"] == 21
    assert score["directional_scored"] == 22
    assert score["directional_accuracy"] == 0.954545
    assert score["best_candidate_correct"] == 3
    assert score["best_candidate_scored"] == 4
    assert score["mean_normalized_regret"] == 0.096154
    assert len(score["abstentions"]) == 1


if __name__ == "__main__":
    test_score()
