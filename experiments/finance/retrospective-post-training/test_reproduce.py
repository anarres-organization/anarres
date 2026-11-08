#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_reproduction() -> None:
    subprocess.run([sys.executable, "scripts/reproduce.py"], cwd=ROOT, check=True)
    summary = json.loads((ROOT / "results" / "summary.json").read_text())
    assert summary["status"] == "retrospective_exploratory"
    assert summary["independent_studies"] == 4
    assert summary["decision_panels"] == 12
    assert summary["trained_intervention_rows_including_controls"] == 47
    assert set(summary["models"]) == {"ridge", "quality_rule", "more_training"}
    assert all(len(model["panels"]) == 12 for model in summary["models"].values())


if __name__ == "__main__":
    test_reproduction()
