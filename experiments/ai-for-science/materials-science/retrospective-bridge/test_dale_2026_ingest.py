import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = Path(__file__).parent / "scripts" / "ingest_dale_2026.py"
SPEC = importlib.util.spec_from_file_location("ingest_dale_2026", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_reconstructs_only_complete_matched_panels(tmp_path):
    for target in ("bandgap", "e_form"):
        for element in ("F", "Fe"):
            for budget in MODULE.BUDGETS:
                for index, method in enumerate(MODULE.METHODS):
                    if (target, element, budget, method) == ("e_form", "F", "0pt05", "random"):
                        continue
                    path = tmp_path / target / element / budget / method / "history_test.json"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(
                        json.dumps(
                            {
                                "loss": [1.0, 0.5 + index / 100],
                                "mae": [0.8, 0.2 + index / 100],
                                "rmse": [0.9, 0.3 + index / 100],
                            }
                        )
                    )

    payload = MODULE.reconstruct(tmp_path)
    assert payload["panel_count"] == 23
    assert payload["arm_count"] == 161
    assert len(payload["excluded_incomplete_panels"]) == 1
    assert {arm["replication"]["exact_released_trajectories"] for arm in payload["arms"]} == {1}


def test_normalization_is_panel_local(tmp_path):
    for index, method in enumerate(MODULE.METHODS):
        path = tmp_path / "bandgap" / "F" / "0pt05" / method / "history_test.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"loss": [index + 1], "mae": [index + 1], "rmse": [index + 1]})
        )
    # Add the other 22 complete panels and the one known incomplete panel.
    for target in ("bandgap", "e_form"):
        for element in ("F", "Fe"):
            for budget in MODULE.BUDGETS:
                if (target, element, budget) == ("bandgap", "F", "0pt05"):
                    continue
                for method in MODULE.METHODS:
                    if (target, element, budget, method) == ("e_form", "F", "0pt05", "random"):
                        continue
                    path = tmp_path / target / element / budget / method / "history_test.json"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps({"loss": [1], "mae": [1], "rmse": [1]}))

    payload = MODULE.reconstruct(tmp_path)
    panel = [
        arm for arm in payload["arms"] if arm["panel_id"].endswith("bandgap:omit_F:budget_0pt05")
    ]
    assert min(arm["derived"]["panel_normalized_regret"] for arm in panel) == 0
    assert max(arm["derived"]["panel_normalized_regret"] for arm in panel) == 1
