import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_exporter():
    path = ROOT / "scripts" / "export_environment_profiles.py"
    spec = importlib.util.spec_from_file_location("agentic_coding_profiles", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_profiles_exclude_training_outcomes(tmp_path):
    paths = load_exporter().export(tmp_path)
    assert len(paths) == 13
    for path in paths:
        profile = json.loads(path.read_text())
        assert profile["schema_version"] == "anarres.environment-profile-input.v1"
        assert "outcomes" not in profile
        assert {row["name"] for row in profile["coordinates"]} >= {"readiness", "reward_information", "mean_log_output_tokens", "target_affinity"}
