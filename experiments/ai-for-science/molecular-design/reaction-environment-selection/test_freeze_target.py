import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "reaction_target_freezer", ROOT / "scripts" / "freeze_target.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def target(target_id: str, status: str = "pass") -> dict[str, object]:
    return {
        "target_id": target_id,
        "receptor_integrity": status,
        "pocket_integrity": status,
        "ligand_fixture_integrity": status,
        "oracle_input_integrity": status,
        "exclusion_reasons": [] if status == "pass" else ["fixture failed"],
    }


def qualification() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "source_archive_sha256": "a" * 64,
        "targets": [target("P12345"), target("Q67890"), target("X11111", "fail")],
    }


def test_target_freeze_is_deterministic_and_outcome_free() -> None:
    first = MODULE.freeze(qualification())
    second_input = qualification()
    second_input["targets"].reverse()
    second = MODULE.freeze(second_input)
    assert first["selected_target_id"] == second["selected_target_id"]
    assert set(first["eligible_target_ids"]) == {"P12345", "Q67890"}
    assert first["outcomes_inspected"] is False


def test_target_freeze_rejects_outcome_fields() -> None:
    payload = qualification()
    payload["targets"][0]["activity"] = 0.9
    with pytest.raises(ValueError, match="unexpected fields"):
        MODULE.freeze(payload)


def test_failed_target_requires_reason() -> None:
    payload = qualification()
    payload["targets"][0]["oracle_input_integrity"] = "fail"
    with pytest.raises(ValueError, match="without an exclusion reason"):
        MODULE.freeze(payload)
