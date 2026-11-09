import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "ingest_etal_2023", ROOT / "scripts" / "ingest_etal_2023.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_etal_derived_artifact():
    payload = json.loads((ROOT / "data" / "zhang_2023_etal_panels.json").read_text())
    assert payload["panel_count"] == 4
    assert payload["arm_count"] == 8
    assert len(payload["arms"]) == 8
    for panel_id in {arm["panel_id"] for arm in payload["arms"]}:
        panel = [arm for arm in payload["arms"] if arm["panel_id"] == panel_id]
        assert len(panel) == 2
        assert max(panel, key=lambda arm: arm["outcome"]["mean_test_r2"])["environment"] == "etal"
        assert {arm["outcome"]["independent_model_fits"] for arm in panel} == {30}
