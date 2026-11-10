import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("run_phonon_panel.py")
SPEC = importlib.util.spec_from_file_location("run_phonon_panel", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_role_shards_are_disjoint_and_complete(tmp_path):
    roles = tmp_path / "roles.json"
    roles.write_text(
        json.dumps({"roles": {"development": ["a", "b", "c", "d", "e"]}}),
        encoding="utf-8",
    )
    shards = [set(MODULE.role_materials(roles, "development", index, 3)) for index in range(3)]
    assert set.union(*shards) == {"a", "b", "c", "d", "e"}
    assert not any(left & right for i, left in enumerate(shards) for right in shards[i + 1 :])


def test_protected_role_combines_development_and_prospective(tmp_path):
    roles = tmp_path / "roles.json"
    roles.write_text(
        json.dumps({"roles": {"development": ["a", "b"], "prospective": ["c", "d"]}}),
        encoding="utf-8",
    )
    assert MODULE.role_materials(roles, "protected", 0, 1) == ["a", "b", "c", "d"]


def test_valid_result_checks_material_identity(tmp_path):
    output = tmp_path / "result.json"
    output.write_text(json.dumps({"material_id": "mp-1", "metrics": {}}), encoding="utf-8")
    assert MODULE.valid_result(output, "mp-1") is True
    assert MODULE.valid_result(output, "mp-2") is False
