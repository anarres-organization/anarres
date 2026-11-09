import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parent / "validate_full_measurements.py"
SPEC = importlib.util.spec_from_file_location("validate_full_measurements", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_validator_accepts_zero_edge_periodic_record(tmp_path):
    manifest = tmp_path / "manifest.jsonl"
    measurements = tmp_path / "records.jsonl"
    summary = tmp_path / "summary.json"
    manifest.write_text(json.dumps({"natoms": 1, "source_family": "isolated"}) + "\n")
    measurements.write_text(
        json.dumps(
            {
                "record_index": 0,
                "natoms": 1,
                "neighbor_edges": 0,
                "force_l2_mean": 0.5,
                "force_mae": 0.25,
                "stress_mae": 0.1,
                "stress_mae_per_atom": 0.1,
            }
        )
        + "\n"
    )
    summary.write_text(
        json.dumps(
            {
                "slice": {"records": 1},
                "model_sha256": "model",
            }
        )
    )
    result = MODULE.validate(manifest, [measurements], [summary])
    assert result["records"] == 1
    assert result["neighbor_edges"] == 0
