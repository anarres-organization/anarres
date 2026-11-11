#!/usr/bin/env python3
"""Integrity checks for the Mint-Agent excluded-source score."""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def test_score() -> None:
    subprocess.run([sys.executable, str(HERE / "score_holdout.py")], check=True)
    score = json.loads((HERE / "SCORE.json").read_text(encoding="utf-8"))
    assert score["directional_correct"] == 4
    assert score["directional_scored"] == 4
    assert score["directional_accuracy"] == 1.0
    assert score["mean_pairwise_regret"] == 0.0


if __name__ == "__main__":
    test_score()
