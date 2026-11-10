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


@pytest.mark.parametrize(
    ("arm", "seed"),
    [("operational_hybrid", 20261108), ("hash_uniform", 17)],
)
def test_unfrozen_arm_or_seed_is_rejected(arm: str, seed: int) -> None:
    with pytest.raises(ValueError):
        MODULE.validate_arm_and_seed(contract(), arm, seed)


def test_replay_artifact_must_bind_frozen_qualification() -> None:
    frozen = contract()
    artifact = {
        "bank": "hash_uniform",
        "item_count": 512,
        "source": {"qualification_sha256": frozen["inputs"]["bank_qualification"]["sha256"]},
    }
    MODULE.validate_replay_artifact(artifact, frozen, "hash_uniform")
    artifact["source"]["qualification_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="frozen qualification"):
        MODULE.validate_replay_artifact(artifact, frozen, "hash_uniform")
