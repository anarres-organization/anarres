import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "customer_support_source_audit", ROOT / "scripts" / "audit_sources.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

STATE_AUDIT_SPEC = importlib.util.spec_from_file_location(
    "state_bench_source_audit", ROOT / "scripts" / "audit_state_bench.py"
)
STATE_AUDIT = importlib.util.module_from_spec(STATE_AUDIT_SPEC)
assert STATE_AUDIT_SPEC.loader is not None
STATE_AUDIT_SPEC.loader.exec_module(STATE_AUDIT)


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

    def test_execution_contracts_remain_train_side(self):
        operator = json.loads((ROOT / "LEARNING_OPERATOR.json").read_text())
        smoke = json.loads((ROOT / "SMOKE_PLAN.json").read_text())
        self.assertEqual(operator["retrieval"]["top_k"], 3)
        self.assertIn("held-out outcomes", operator["exclusions"])
        self.assertEqual(
            smoke["scientific_use"], "development only; never treated as held-out evidence"
        )
        self.assertEqual(len(smoke["task_ids"]), len(smoke["task_family_counts"]))

    def test_tracked_change_check_ignores_only_untracked_files(self):
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
            tracked = checkout / "tracked.txt"
            tracked.write_text("original\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=checkout, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Anarres Test",
                    "-c",
                    "user.email=tests@example.invalid",
                    "commit",
                    "-qm",
                    "fixture",
                ],
                cwd=checkout,
                check=True,
            )
            (checkout / "extension.py").write_text("untracked\n", encoding="utf-8")
            self.assertEqual(STATE_AUDIT.tracked_changes(checkout), [])
            tracked.write_text("modified\n", encoding="utf-8")
            self.assertTrue(STATE_AUDIT.tracked_changes(checkout))


if __name__ == "__main__":
    unittest.main()
