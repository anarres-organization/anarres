import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_exporter():
    path = ROOT / "scripts" / "export_external_profiles.py"
    spec = importlib.util.spec_from_file_location("agentic_coding_external_profiles", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_external_profiles_are_outcome_free(tmp_path):
    paths = load_exporter().export(tmp_path)
    assert len(paths) == 16
    for path in paths:
        profile = json.loads(path.read_text())
        assert profile["schema_version"] == "anarres.environment-profile-input.v1"
        assert "score" not in profile
        assert "outcomes" not in profile
        assert "policy_aligned_progression" in {row["name"] for row in profile["coordinates"]}
