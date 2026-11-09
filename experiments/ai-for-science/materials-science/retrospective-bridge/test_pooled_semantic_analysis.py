import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "analyze_pooled_semantic", ROOT / "scripts" / "analyze_pooled_semantic.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_pooled_semantic_analysis_support_and_boundaries():
    result = MODULE.analyze(ROOT / "data")
    assert result["support"] == {"sources": 16, "panels": 804, "arms": 3002}
    assert set(result["fold_alphas"]) == set(MODULE.FILES)
    for family in ("panel_weighted_metrics", "source_macro_metrics"):
        assert set(result[family]) == {"uninformed_tie", "semantic_mean", "ridge"}
        for values in result[family].values():
            assert 0.0 <= values["pairwise_ordering"] <= 1.0
            assert 0.0 <= values["mean_normalized_regret"] <= 1.0
            assert 0.0 <= values["top_choice_credit"] <= 1.0
    semantic_counts = result["source_win_counts_vs_uninformed_tie"]["semantic_mean"]
    assert semantic_counts["pairwise_ordering"] == {
        "improved": 15,
        "tied": 0,
        "worsened": 1,
    }
    assert semantic_counts["mean_normalized_regret"] == {
        "improved": 14,
        "tied": 0,
        "worsened": 2,
    }
    assert any("No source" in line for line in result["interpretation_boundary"])
