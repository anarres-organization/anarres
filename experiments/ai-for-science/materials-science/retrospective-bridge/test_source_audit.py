import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "audit_sources.py"
SPEC = importlib.util.spec_from_file_location("materials_source_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_source_ledger_is_valid():
    payload = MODULE.validate()
    statuses = {source["id"]: source["status"] for source in payload["sources"]}
    assert statuses["li_2023_redundancy"] == "included"
    assert statuses["haenseroth_2026_generators"] == "included"
    assert statuses["lin_2026_zif_sampling"] == "pending_numerical_reconciliation"
    assert statuses["radova_2025_frozen_transfer"] == "pending_result_artifact"
    assert statuses["unglert_2026_rens_active_learning"] == "context_only"
    assert statuses["khan_2026_active_learning_strategies"] == "excluded_unverified_release"
