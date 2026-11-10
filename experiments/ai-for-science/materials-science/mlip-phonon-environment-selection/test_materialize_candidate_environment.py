import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("materialize_candidate_environment.py")
SPEC = importlib.util.spec_from_file_location("materialize_candidate_environment", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_candidate_lookup_uses_exact_frozen_identifier(tmp_path):
    panel = tmp_path / "panel.json"
    panel.write_text(
        json.dumps(
            {
                "candidates": [
                    {"candidate_id": "alpha", "record_indices": [0]},
                    {"candidate_id": "beta", "record_indices": [1]},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert MODULE.candidate_from_panel(panel, "beta")["record_indices"] == [1]


def test_candidate_lookup_rejects_unknown_identifier(tmp_path):
    panel = tmp_path / "panel.json"
    panel.write_text(json.dumps({"candidates": []}), encoding="utf-8")
    try:
        MODULE.candidate_from_panel(panel, "missing")
    except ValueError as error:
        assert "expected one frozen candidate" in str(error)
    else:
        raise AssertionError("unknown candidate was accepted")


def test_membership_hash_preserves_frozen_order():
    class Row:
        def __init__(self, sid):
            self.data = {"sid": sid}

    first = MODULE.membership_sha256([Row("a"), Row("b")])
    second = MODULE.membership_sha256([Row("b"), Row("a")])
    assert first != second
