import json
from pathlib import Path

ROOT = Path(__file__).parent


def test_qualification_does_not_consume_final_candidate_outcomes():
    protocol = json.loads((ROOT / "TRAINING_QUALIFICATION_PROTOCOL.json").read_text())
    final_panel = json.loads((ROOT / "FINAL_COST_MATCHED_PANEL.json").read_text())
    final_ids = {candidate["candidate_id"] for candidate in final_panel["candidates"]}
    qualification = protocol["qualification_environment"]
    assert qualification["candidate_id"] not in final_ids
    assert qualification["included_in_final_panel"] is False
    assert protocol["qualification_grid"]["uses_phonon_target_outcomes"] is False


def test_claim_training_preserves_frozen_development_to_prospective_order():
    protocol = json.loads((ROOT / "TRAINING_QUALIFICATION_PROTOCOL.json").read_text())
    claim = protocol["proposed_claim_training_after_qualification"]
    assert claim["development_environments"] == 12
    assert claim["prospective_environments"] == 4
    assert claim["checkpoint_after_each_pass"] is True
    assert claim["training_seeds"] == [0, 1]


def test_training_labels_remain_separate_from_phonon_outcomes():
    protocol = json.loads((ROOT / "TRAINING_QUALIFICATION_PROTOCOL.json").read_text())
    labels = protocol["label_contract"]
    assert labels["energy_weight"] == 0.0
    assert labels["force_weight"] > 0
    assert labels["stress_weight"] > 0
    assert "Phonons are held-out physical outcomes" in labels["rationale"]
