from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "verify_matched_training_contract.py"
SPEC = importlib.util.spec_from_file_location("verify_matched_training_contract", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_committed_matched_training_contract_is_verified() -> None:
    result = MODULE.verify()
    assert result["status"] == "verified"
    assert result["development_arms"] == 6
    assert result["training_seeds"] == 2
    assert result["maximum_target_oracle_attempts"] == 40000
    assert result["development_or_prospective_outcomes_opened"] is False


def test_evaluation_seed_derivation_is_stable() -> None:
    assert MODULE.expected_evaluation_seed(20261108, 200) == 835155383
    assert MODULE.expected_evaluation_seed(20261109, 625) == 53252595
