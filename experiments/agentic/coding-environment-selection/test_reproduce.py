import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_reproduce():
    path = ROOT / "scripts" / "reproduce.py"
    spec = importlib.util.spec_from_file_location("agentic_coding_reproduce", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_released_summary_recomputes():
    module = load_reproduce()
    actual = module.compute(json.loads((ROOT / "data" / "panels.json").read_text()))
    expected = json.loads((ROOT / "results" / "summary.json").read_text())
    assert actual == expected


def test_independent_decisions_are_not_endpoint_count():
    summary = json.loads((ROOT / "results" / "summary.json").read_text())
    assert summary["independent_training_decisions"] == 2
    assert summary["nested_reported_endpoints"] == 4
    assert summary["aggregate"]["policy_response_rule"]["mean_regret_pp"] == 0.1
    assert summary["aggregate"]["reward_information"] == summary["aggregate"]["policy_response_rule"]
