import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class FinanceProtocolTest(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads((ROOT / "PROTOCOL.json").read_text())

    def test_protocol_is_explicitly_unfrozen(self):
        self.assertIn("NOT_FROZEN", self.protocol["status"])
        self.assertTrue(self.protocol["unresolved_before_freeze"])

    def test_outcome_lock_precedes_training(self):
        chronology = self.protocol["chronology"]
        serialized = next(i for i, step in enumerate(chronology) if "serialize" in step)
        trained = next(i for i, step in enumerate(chronology) if "train and evaluate" in step)
        opened = next(i for i, step in enumerate(chronology) if "open held-out" in step)
        self.assertLess(serialized, trained)
        self.assertLess(trained, opened)

    def test_material_controls_remain_separate(self):
        self.assertIn("approval_policy_violations", self.protocol["guardrails"])
        self.assertIn(
            "pooling accounting, research, and authority-bearing outcomes into one score",
            self.protocol["prohibitions"],
        )


if __name__ == "__main__":
    unittest.main()
