from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "regression", ROOT / "scripts" / "reproduce_regression_risk.py"
)
assert SPEC and SPEC.loader
REGRESSION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REGRESSION)


class RegressionRiskTest(unittest.TestCase):
    def test_summary_reproduces(self) -> None:
        self.assertEqual(
            REGRESSION.compute(),
            json.loads((ROOT / "results" / "regression-risk-summary.json").read_text()),
        )

    def test_claim_bearing_counts_and_controls(self) -> None:
        summary = REGRESSION.compute()
        self.assertEqual(summary["seed_target_outcomes"], 24)
        self.assertEqual(summary["regressions"], 5)
        self.assertEqual(summary["audited_seed_target_regressions"], 0)
        self.assertEqual(summary["high_risk_group"]["regressions_captured"], 5)
        self.assertGreater(
            summary["risk_rule"]["roc_auc"], summary["starting_pass_rate"]["roc_auc"]
        )


if __name__ == "__main__":
    unittest.main()
