from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "task_regression", ROOT / "scripts" / "reproduce_task_regression.py"
)
assert SPEC and SPEC.loader
TASK_REGRESSION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TASK_REGRESSION)


class TaskRegressionTest(unittest.TestCase):
    def test_summary_reproduces(self) -> None:
        self.assertEqual(
            TASK_REGRESSION.compute(),
            json.loads((ROOT / "results" / "task-regression-summary.json").read_text()),
        )

    def test_support_split_and_negative_control(self) -> None:
        summary = TASK_REGRESSION.compute()
        self.assertEqual(summary["held_out_repositories"], 22)
        self.assertEqual(summary["task_environment_outcomes"], 4140)
        self.assertEqual(summary["severe_regressions"], 476)
        self.assertGreater(summary["combined_auc"], summary["starting_behavior_auc"])
        self.assertGreater(summary["combined_auc_gain_repository_clustered_ci95"][0], 0)


if __name__ == "__main__":
    unittest.main()
