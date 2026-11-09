import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "analyze_source_specific.py"
SPEC = importlib.util.spec_from_file_location("analyze_source_specific", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_metrics_distinguish_tie_from_perfect_ordering():
    rows = [
        {"panel": "a", "utility": 1.0},
        {"panel": "a", "utility": 0.0},
        {"panel": "b", "utility": 0.25},
        {"panel": "b", "utility": 0.75},
    ]
    tie = MODULE.metrics(rows, [0.0, 0.0, 0.0, 0.0])
    perfect = MODULE.metrics(rows, [1.0, 0.0, 0.25, 0.75])
    assert tie["pairwise_ordering"] == 0.5
    assert tie["mean_normalized_regret"] == 0.375
    assert perfect["pairwise_ordering"] == 1.0
    assert perfect["mean_normalized_regret"] == 0.0
    assert perfect["top_choice_credit"] == 1.0


def test_checked_in_analysis_has_expected_support():
    data = Path(__file__).parent / "data"
    payload = MODULE.analyze(data)
    assert payload["support"] == {"sources": 16, "panels": 828, "arms": 2990}
    assert payload["sources"]["dale_2026_active_learning_failure"]["support"]["panels"] == 23
    assert payload["sources"]["liu_2026_heterogeneous_uq"]["support"] == {
        "groups": 2,
        "panels": 2,
        "arms": 12,
    }
    assert payload["sources"]["haenseroth_dressler_2026_data_efficiency"]["support"] == {
        "groups": 7,
        "panels": 336,
        "arms": 672,
    }
