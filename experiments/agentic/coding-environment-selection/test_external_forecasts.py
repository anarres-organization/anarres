import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_reproduce():
    path = ROOT / "scripts" / "reproduce_external_forecasts.py"
    spec = importlib.util.spec_from_file_location("agentic_coding_external", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_external_forecast_summary_recomputes():
    module = load_reproduce()
    panels = json.loads((ROOT / "data" / "external-forecast-panels.json").read_text())
    actual = module.compute(panels)
    expected = json.loads((ROOT / "results" / "external-forecast-summary.json").read_text())
    assert actual == expected


def test_external_check_preserves_chronology_and_source_separation():
    data = json.loads((ROOT / "data" / "external-forecast-panels.json").read_text())
    summary = json.loads((ROOT / "results" / "external-forecast-summary.json").read_text())
    assert data["chronology"] == "retrospective_source_separated_external_check"
    assert summary["matched_training_decisions"] == 6
    assert summary["aggregate"]["policy_aligned_progression_rule"] == {
        "best_candidate_decisions": 6,
        "pairwise_correct": 10,
        "pairwise_total": 10,
    }
    blocks = summary["aggregate"]["source_blocks"]
    assert blocks["auto_env_scaling"]["source_baseline_mean_regret_pp"] == 5.45
    assert blocks["environment_evolution"]["source_baseline_mean_regret_pp"] == 11.8
