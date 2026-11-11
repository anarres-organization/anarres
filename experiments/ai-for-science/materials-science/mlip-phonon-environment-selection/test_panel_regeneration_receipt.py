import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_regeneration_receipt_matches_released_artifacts():
    receipt = json.loads((HERE / "PANEL_REGENERATION_RECEIPT.json").read_text())
    panel_path = HERE / receipt["original_artifact"]["path"]
    panel = json.loads(panel_path.read_text())

    assert sha256(panel_path) == receipt["original_artifact"]["sha256"]
    assert panel_path.stat().st_size == receipt["original_artifact"]["bytes"]
    assert receipt["regeneration_result"]["sha256"] == sha256(panel_path)
    assert receipt["regeneration_result"]["byte_identical_to_original"] is True

    canonical_inputs = json.dumps(panel["inputs"], sort_keys=True, separators=(",", ":")).encode()
    assert (
        hashlib.sha256(canonical_inputs).hexdigest()
        == receipt["input_identity"]["canonical_json_sha256"]
    )
    assert panel["inputs"]["manifest_sha256"] == receipt["input_identity"]["manifest_sha256"]
    assert (
        len(panel["inputs"]["measurement_sha256"])
        == receipt["input_identity"]["measurement_shards"]
    )
    assert (
        len(panel["inputs"]["target_yaml_sha256"]) == receipt["input_identity"]["target_yaml_files"]
    )


def test_regeneration_receipt_pins_code_and_solver_environment():
    receipt = json.loads((HERE / "PANEL_REGENERATION_RECEIPT.json").read_text())
    locked = receipt["locked_environment"]
    code = receipt["code_and_lock"]

    assert locked["python_version"] == "3.11.7"
    assert locked["numpy_version"] == "2.4.6"
    assert locked["scipy_version"] == "1.17.1"
    assert locked["platform"] == "macOS-26.4-arm64-arm-64bit"
    assert "multiple" in locked["solver_note"].lower()

    assert (
        sha256(HERE / "construct_cost_matched_panel.py")
        == code["construct_cost_matched_panel.py_sha256"]
    )
    assert (
        sha256(HERE / "construct_candidate_bank.py") == code["construct_candidate_bank.py_sha256"]
    )
    assert sha256(HERE / "PANEL_REGENERATION_PYPROJECT.toml") == code["pyproject.toml_sha256"]
    assert (
        sha256(HERE / "PANEL_REGENERATION_REQUIREMENTS.txt")
        == code["PANEL_REGENERATION_REQUIREMENTS.txt_sha256"]
    )

    command = receipt["command"]
    assert "--no-project" in command
    assert command[command.index("--python") + 1] == "3.11.7"
    assert "--with-requirements" in command
    assert command[command.index("--time-limit-seconds") + 1] == "60"
