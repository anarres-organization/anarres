import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "audit_sources", ROOT / "scripts" / "audit_sources.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FinanceSourceAuditTest(unittest.TestCase):
    def setUp(self):
        self.sources = json.loads((ROOT / "SOURCES.json").read_text())
        self.preflight = json.loads((ROOT / "PREFLIGHT.json").read_text())

    def test_source_registry(self):
        MODULE.validate_sources(self.sources)

    def test_preflight_record(self):
        MODULE.validate_preflight(self.preflight, self.sources)

    def test_construction_source_is_pinned(self):
        construction = [
            source
            for source in self.sources["sources"]
            if source["role"] == "construction_candidate"
        ]
        self.assertEqual(len(construction), 1)
        self.assertEqual(len(construction[0]["revision"]), 40)


if __name__ == "__main__":
    unittest.main()
