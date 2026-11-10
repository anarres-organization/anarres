import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "audit_prospective_results", ROOT / "audit_prospective_results.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_checked_in_post_prospective_audit_regenerates_exactly():
    observed = MODULE.build_audit(
        ROOT / "FINAL_COST_MATCHED_PANEL.json",
        ROOT / "DEVELOPMENT_OUTCOMES.json",
        ROOT / "AGGREGATE_UTILITY_FIT.json",
        ROOT / "TARGET_REGRESSION_FIT.json",
        ROOT / "PROSPECTIVE_OUTCOMES.json",
        ROOT / "PROSPECTIVE_PREDICTION_SCORE.json",
    )
    expected = json.loads((ROOT / "POST_PROSPECTIVE_AUDIT.json").read_text())
    assert observed == expected


def test_support_audit_preserves_the_failed_forecast_boundary():
    audit = json.loads((ROOT / "POST_PROSPECTIVE_AUDIT.json").read_text())
    boundary = audit["evidence_boundary"]
    assert boundary["frozen_forecast_modified"] is False
    assert boundary["support_guard_prespecified"] is False
    assert audit["decision_audit"]["would_abstain_at_all_budgets"] is True
    assert audit["observed_boundary"]["selected_environment_worst_at_all_budgets"] is True
    assert audit["observed_boundary"]["no_training_option_best_at_all_budgets"] is True
    source_audit = audit["development_leave_source_family_out"]
    assert source_audit["largest_error_fold"] == "rattled-relax"
    assert audit["selected_model"]["environment_coefficient"]["coefficient"] < 0
