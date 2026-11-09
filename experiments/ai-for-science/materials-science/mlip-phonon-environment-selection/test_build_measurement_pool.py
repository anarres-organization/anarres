import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).parent / "build_measurement_pool.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("build_measurement_pool", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_source_family_merges_rattled_subsamples():
    assert MODULE.source_family("rattled-300-subsampled") == "rattled-300"
    assert MODULE.source_family("rattled-300") == "rattled-300"
    assert MODULE.source_family("aimd-from-PBE-1000-nvt") == "aimd-from-PBE-1000-nvt"


def test_record_hash_is_deterministic_and_source_specific():
    first = MODULE.record_score("rattled-300", "record-1")
    assert first == MODULE.record_score("rattled-300", "record-1")
    assert first != MODULE.record_score("rattled-500", "record-1")
