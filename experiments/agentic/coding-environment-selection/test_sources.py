import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_source_registry_has_unique_ids_and_audited_claim_sources():
    sources = json.loads((ROOT / "SOURCES.json").read_text())["sources"]
    ids = [source["id"] for source in sources]
    assert len(ids) == len(set(ids))
    admitted = {source["id"]: source for source in sources if source["status"] == "admitted"}
    assert set(admitted) == {"tmax", "rlve"}
    assert all(source.get("license") for source in admitted.values())
    external = {source["id"]: source for source in sources if source["status"] == "external_check"}
    assert {"auto_env_scaling", "environment_evolution"} <= set(external)
    assert all(source.get("revision") and source.get("license") for source in external.values())


def test_mechanism_sources_are_not_pooled_with_selector_panels():
    records = json.loads((ROOT / "data" / "mechanism-evidence.json").read_text())["records"]
    assert records
    assert all(record["pool_with_selector_panels"] is False for record in records)
