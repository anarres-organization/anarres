import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "reaction_target_panel_freezer",
    ROOT / "scripts" / "freeze_target_panel.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def archive_audit() -> dict[str, object]:
    return {
        "archive": {"sha256": "a" * 64},
        "target_fixtures": {"target_ids": ["P12345", "Q67890", "O11111", "P99999"]},
        "sealed_boundary": {
            "outcome_file_contents_read": False,
            "reference_active_contents_read": False,
            "published_model_results_read": False,
        },
    }


def test_panel_freeze_is_deterministic() -> None:
    first = MODULE.freeze(archive_audit(), 3)
    second_input = archive_audit()
    second_input["target_fixtures"]["target_ids"].reverse()
    second = MODULE.freeze(second_input, 3)
    assert first["target_ids"] == second["target_ids"]
    assert len(first["target_ids"]) == 3
    assert first["outcomes_inspected"] is False


def test_panel_freeze_rejects_opened_outcomes() -> None:
    payload = archive_audit()
    payload["sealed_boundary"]["published_model_results_read"] = True
    with pytest.raises(ValueError, match="must remain unopened"):
        MODULE.freeze(payload, 3)


def test_panel_size_cannot_exceed_inventory() -> None:
    with pytest.raises(ValueError, match="exceeds"):
        MODULE.freeze(archive_audit(), 5)
