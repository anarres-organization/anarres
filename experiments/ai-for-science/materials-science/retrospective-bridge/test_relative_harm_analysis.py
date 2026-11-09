import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "analyze_relative_harm", ROOT / "scripts" / "analyze_relative_harm.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_relative_harm_support_references_and_controls():
    rows = MODULE.load_pairs(ROOT / "data")
    assert len({row["source"] for row in rows}) == 13
    assert len({(row["source"], row["panel"]) for row in rows}) == 787
    assert len(rows) == 2136
    assert all(row["candidate"] != row["reference"] for row in rows)

    result = MODULE.evaluate(rows, MODULE.PRIMARY_MARGIN, tune=True)
    semantic = result["semantic_relative_score"]["source_macro"]
    ridge = result["fitted_logistic_ridge"]["source_macro"]
    prevalence = result["prevalence_baseline"]["source_macro"]
    random_control = result["random_fingerprint_control"]["source_macro"]
    shuffled_control = result["shuffled_pairing_control"]["source_macro"]

    assert semantic["roc_auc"] > ridge["roc_auc"]
    assert semantic["roc_auc"] > random_control["roc_auc"]
    assert semantic["roc_auc"] > shuffled_control["roc_auc"]
    assert semantic["brier_score"] < prevalence["brier_score"]
    assert semantic["recall_in_top_risk_20pct"] > prevalence["recall_in_top_risk_20pct"]
