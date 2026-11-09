import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "ingest_moerman_2026.py"
SPEC = importlib.util.spec_from_file_location("moerman_ingest", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def source_fixture(tmp_path: Path) -> Path:
    metrics = {}
    for offset, source_metric in enumerate(MODULE.METRICS.values()):
        domains = {}
        for domain_offset, domain in enumerate(MODULE.DOMAINS):
            values = {
                selector: 0.1 + offset + domain_offset + rank / 100
                for rank, selector in enumerate(MODULE.SELECTORS)
            }
            domains[domain] = {"geometric_mean": {"values": values}}
        metrics[source_metric] = {"domains": domains}
    path = tmp_path / "paper_tables.json"
    path.write_text(json.dumps({"metrics": metrics}), encoding="utf-8")
    return path


def test_reconstructs_matched_budget_selector_panels(tmp_path):
    payload = MODULE.reconstruct(source_fixture(tmp_path))
    assert payload["panel_count"] == 6
    assert payload["arm_count"] == 36
    assert payload["role"].endswith("excluded from predictive fitting")
    assert {arm["selector_family"] for arm in payload["arms"]} == {"EnvTok", "DIRECT", "random"}
    assert all(
        arm["pre_outcome_measurements"]["training_atom_count"] > 6_490_000
        for arm in payload["arms"]
    )
    assert all(0 <= arm["derived"]["panel_normalized_utility"] <= 1 for arm in payload["arms"])


def test_checked_in_artifact_matches_reconstruction():
    artifact = Path(__file__).parent / "data" / "moerman_2026_omat24_selector_panels.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["panel_count"] == 6
    assert payload["arm_count"] == 36
    assert payload["source_artifact"]["sha256"] == (
        "3de131cecab9e72d2218f9fb77b5b6836e60a1c454410119d546ac30a1660b48"
    )
    panels = {}
    for arm in payload["arms"]:
        panels.setdefault(arm["panel_id"], []).append(arm)
    for panel_id, arms in panels.items():
        winner = max(arms, key=lambda arm: arm["derived"]["native_utility"])
        expected = "EnvTok" if ":bulk:" in panel_id else "DIRECT"
        assert winner["selector_family"] == expected
