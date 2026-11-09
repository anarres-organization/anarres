import json
from pathlib import Path


DATA = (
    Path(__file__).parent
    / "data"
    / "kuner_2025_mp_aloe_cost_sensitive_audit.json"
)


def test_mp_aloe_audit_preserves_reported_winners_and_cost_boundary():
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    assert payload["comparison_contract"]["matched_training_cost"] is False
    panels = {panel["panel_id"]: panel for panel in payload["panels"]}
    assert panels["wbm_equilibrium_cohesive_energy"]["winner"] == "matpes"
    assert panels["extreme_static_compression"]["winner"] == "combined"
    assert panels["extreme_temperature_nvt"]["winner"] == "mp_aloe"
    assert panels["extreme_temperature_pressure_npt"]["winner"] == "combined"


def test_mp_aloe_winners_follow_metric_direction():
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    for panel in payload["panels"]:
        outcomes = panel["outcomes"]
        if panel["direction"] == "lower_is_better":
            winner = min(outcomes, key=outcomes.get)
        else:
            winner = max(outcomes, key=outcomes.get)
        assert winner == panel["winner"]
