import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("evaluate_phonon_panel.py")
SPEC = importlib.util.spec_from_file_location("evaluate_phonon_panel", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_role_and_result_identity_are_enforced(tmp_path):
    roles = tmp_path / "roles.json"
    roles.write_text(json.dumps({"roles": {"development": ["mp-1", "mp-2"]}}), encoding="utf-8")
    assert MODULE.role_materials(roles, "development") == ["mp-1", "mp-2"]

    result = tmp_path / "mp-1.json"
    result.write_text(
        json.dumps({"material_id": "mp-1", "model_sha256": "digest", "metrics": {}}),
        encoding="utf-8",
    )
    assert MODULE.valid_result(result, "mp-1", "digest")
    assert not MODULE.valid_result(result, "mp-1", "different")
