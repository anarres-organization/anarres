from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "run_matched_training.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("run_matched_training", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def contract() -> dict:
    return json.loads((ROOT / "MATCHED_TRAINING_EVALUATION_CONTRACT_V1.json").read_text())


def test_frozen_development_arm_and_seed_are_accepted() -> None:
    MODULE.validate_arm_and_seed(contract(), "graph_embedding_coverage", 20261109)


def test_frozen_prospective_arm_and_seed_are_accepted() -> None:
    MODULE.validate_arm_and_seed(contract(), "operational_hybrid", 20261108, "prospective")


@pytest.mark.parametrize(
    ("arm", "seed"),
    [("operational_hybrid", 20261108), ("hash_uniform", 17)],
)
def test_unfrozen_arm_or_seed_is_rejected(arm: str, seed: int) -> None:
    with pytest.raises(ValueError):
        MODULE.validate_arm_and_seed(contract(), arm, seed)


def test_replay_artifact_must_bind_frozen_qualification() -> None:
    frozen = contract()
    items = [{"x": 1}, {"x": 2}]
    artifact = {
        "bank": "hash_uniform",
        "item_count": len(items),
        "items": items,
        "items_sha256": MODULE.canonical_json_sha256(items),
        "source": {"qualification_sha256": frozen["inputs"]["bank_qualification"]["sha256"]},
    }
    frozen["development_panel"]["bank_size"] = len(items)
    expected = frozen["inputs"]["bank_qualification"]["sha256"]
    MODULE.validate_replay_artifact(artifact, frozen, "hash_uniform", expected)
    artifact["source"]["qualification_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="frozen qualification"):
        MODULE.validate_replay_artifact(artifact, frozen, "hash_uniform", expected)


def test_replay_artifact_payload_hash_is_verified() -> None:
    frozen = contract()
    frozen["development_panel"]["bank_size"] = 1
    artifact = {
        "bank": "hash_uniform",
        "item_count": 1,
        "items": [{"x": 1}],
        "items_sha256": "0" * 64,
        "source": {"qualification_sha256": frozen["inputs"]["bank_qualification"]["sha256"]},
    }
    with pytest.raises(ValueError, match="item hash"):
        MODULE.validate_replay_artifact(
            artifact,
            frozen,
            "hash_uniform",
            frozen["inputs"]["bank_qualification"]["sha256"],
        )


def test_prospective_replay_must_match_frozen_membership() -> None:
    frozen = contract()
    frozen["development_panel"]["bank_size"] = 1
    items = [{"anarres_record_id": "a"}]
    artifact = {
        "bank": "operational_hybrid",
        "item_count": 1,
        "items": items,
        "items_sha256": MODULE.canonical_json_sha256(items),
        "source": {
            "qualification_sha256": "1" * 64,
            "record_ids_line_sha256": "2" * 64,
        },
    }
    MODULE.validate_replay_artifact(
        artifact,
        frozen,
        "operational_hybrid",
        "1" * 64,
        "2" * 64,
    )
    with pytest.raises(ValueError, match="forecast freeze"):
        MODULE.validate_replay_artifact(
            artifact,
            frozen,
            "operational_hybrid",
            "1" * 64,
            "3" * 64,
        )


def test_prepared_target_hashes_are_verified(tmp_path: Path) -> None:
    receptor = tmp_path / "receptor.pdbqt"
    reference = tmp_path / "reference_ligand.sdf"
    receptor.write_text("receptor\n")
    reference.write_text("reference\n")
    manifest = {
        "receptor_pdbqt": receptor.name,
        "reference_ligand": reference.name,
        "fixture_sha256": {
            "prepared_receptor": MODULE.sha256_file(receptor),
            "reference_ligand": MODULE.sha256_file(reference),
        },
    }
    (tmp_path / "target_manifest.json").write_text(json.dumps(manifest))
    identity = MODULE.validate_prepared_target(tmp_path)
    assert identity["prepared_receptor_sha256"] == MODULE.sha256_file(receptor)
    receptor.write_text("changed\n")
    with pytest.raises(ValueError, match="prepared receptor hash"):
        MODULE.validate_prepared_target(tmp_path)


def test_released_accelerator_smoke_is_required() -> None:
    report = MODULE.validate_accelerator_smoke()
    assert report["execution"]["device"] == "cuda"
    assert report["smoke_batch"] == {"online": 64, "replay": 64, "updates": 1}
    assert all(report["checks"].values())
