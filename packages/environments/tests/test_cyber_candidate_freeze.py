import importlib.util
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "experiments"
    / "cyber"
    / "qualification"
    / "freeze_development_candidates.py"
)
SPEC = importlib.util.spec_from_file_location("cyber_candidate_freeze", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CyberCandidateFreezeTest(unittest.TestCase):
    def test_order_is_deterministic_and_deduplicated(self) -> None:
        rows = MODULE.ordered_rows("cybergym", ["task-b", "task-a", "task-b"])
        self.assertEqual(len(rows), 2)
        self.assertEqual([row["position"] for row in rows], [1, 2])
        self.assertEqual(
            rows,
            sorted(rows, key=lambda row: (row["rank_sha256"], row["task_id"])),
        )

    def test_rank_is_namespaced_by_family(self) -> None:
        self.assertNotEqual(
            MODULE.rank("cybergym", "task-a"),
            MODULE.rank("sec_bench_pro", "task-a"),
        )


if __name__ == "__main__":
    unittest.main()
