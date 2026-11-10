import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("freeze_final_training_contract.py")
SPEC = importlib.util.spec_from_file_location("freeze_final_training_contract", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_contract_binds_qualified_training_and_preserves_outcome_boundary(tmp_path):
    panel = tmp_path / "panel.json"
    panel.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "candidate_id": f"d-{index}",
                        "membership_sha256": str(index),
                        "role": "development",
                    }
                    for index in range(12)
                ]
                + [
                    {
                        "candidate_id": f"p-{index}",
                        "membership_sha256": str(index),
                        "role": "prospective",
                    }
                    for index in range(4)
                ]
            }
        ),
        encoding="utf-8",
    )
    roles = tmp_path / "roles.json"
    roles.write_text("{}", encoding="utf-8")
    protocol = tmp_path / "protocol.json"
    protocol.write_text(
        json.dumps(
            {
                "qualification_grid": {"learning_rates": [1e-4]},
                "starting_checkpoint": {"sha256": "m"},
                "implementation": {
                    "upstream_repository": "https://example.test/nequix",
                    "upstream_commit": "abc",
                    "upstream_version": "0.4.5",
                },
            }
        ),
        encoding="utf-8",
    )
    qualification = tmp_path / "qualification.json"
    qualification.write_text(
        json.dumps(
            {
                "protocol_sha256": MODULE.sha256(protocol),
                "status": "complete_before_final_candidate_training",
                "selected_learning_rate": 1e-4,
            }
        ),
        encoding="utf-8",
    )
    targets = tmp_path / "targets.json"
    targets.write_text(
        json.dumps(
            {
                "status": "complete_before_candidate_training",
                "target_roles_sha256": MODULE.sha256(roles),
            }
        ),
        encoding="utf-8",
    )
    patch = tmp_path / "patch"
    patch.write_text("patch", encoding="utf-8")
    config = tmp_path / "config.py"
    config.write_text("config", encoding="utf-8")
    result = MODULE.freeze(panel, roles, protocol, qualification, targets, patch, config)
    assert len(result["environments"]["development"]) == 12
    assert result["optimization"]["learning_rate"] == 1e-4
    assert not any(result["outcome_boundary"].values())
