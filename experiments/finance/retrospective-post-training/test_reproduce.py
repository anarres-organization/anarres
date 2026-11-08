#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_panel_registry() -> None:
    panels = json.loads((ROOT / "data" / "panels.json").read_text())
    sources = json.loads((ROOT / "SOURCES.json").read_text())
    source_ids = {source["id"] for source in sources["sources"]}
    panel_ids = [panel["panel_id"] for panel in panels["panels"]]
    assert len(panel_ids) == len(set(panel_ids))
    assert {panel["study_id"] for panel in panels["panels"]} == source_ids
    for panel in panels["panels"]:
        arm_ids = [arm["id"] for arm in panel["arms"]]
        assert panel["baseline"] in arm_ids
        assert len(arm_ids) == len(set(arm_ids))
        assert all(len(arm["features"]) == len(panels["feature_names"]) for arm in panel["arms"])


def test_reproduction() -> None:
    subprocess.run([sys.executable, "scripts/reproduce.py"], cwd=ROOT, check=True)
    summary = json.loads((ROOT / "results" / "summary.json").read_text())
    assert summary["status"] == "retrospective_exploratory"
    assert summary["independent_studies"] == 4
    assert summary["decision_panels"] == 12
    assert summary["trained_intervention_rows_including_controls"] == 47
    assert set(summary["models"]) == {"ridge", "quality_rule", "more_training"}
    assert all(len(model["panels"]) == 12 for model in summary["models"].values())
    assert summary["models"]["quality_rule"]["top_choice_accuracy"] == 0.833333
    assert summary["models"]["ridge"]["normalized_rmse"] == 0.573121


if __name__ == "__main__":
    test_panel_registry()
    test_reproduction()
