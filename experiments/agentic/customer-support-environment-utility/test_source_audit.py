import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "customer_support_source_audit", ROOT / "scripts" / "audit_sources.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CustomerSupportSourceAuditTest(unittest.TestCase):
    def test_records_are_consistent(self):
        sources, protocol, qualification = MODULE.validate()
        self.assertEqual(protocol["source"]["primary"], "state_bench")
        self.assertEqual(qualification["source_audit"]["training_trajectory_count"], 100)
        self.assertEqual(qualification["source_audit"]["test_split_count"], 50)
        self.assertFalse(qualification["scientific_outcomes_opened"])
        self.assertEqual(len(sources["sources"]), 3)

    def test_primary_source_is_pinned(self):
        sources = json.loads((ROOT / "SOURCES.json").read_text(encoding="utf-8"))
        state_bench = next(source for source in sources["sources"] if source["id"] == "state_bench")
        self.assertEqual(len(state_bench["revision"]), 40)
        self.assertEqual(state_bench["outcome_use"], "none")


if __name__ == "__main__":
    unittest.main()
