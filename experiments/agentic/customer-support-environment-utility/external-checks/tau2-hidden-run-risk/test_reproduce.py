import json
import subprocess
import sys
import unittest
from pathlib import Path

STUDY = Path(__file__).resolve().parent


class HiddenRunRiskTest(unittest.TestCase):
    def test_reproducer(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(STUDY / "scripts/reproduce.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        summary = json.loads(completed.stdout)
        self.assertEqual(summary["status"], "reproduced")
        self.assertEqual(summary["development_folds"], 8)
        self.assertEqual(summary["frozen_target_tasks"], 114)
        self.assertAlmostEqual(summary["task_failure_auc"], 0.8820233585858586)
        self.assertAlmostEqual(summary["absolute_pass_rate_error"], 0.003654970760234022)

    def test_claim_boundary(self) -> None:
        protocol = json.loads((STUDY / "PROTOCOL.json").read_text())
        self.assertIn("inference-time model run", protocol["claim_boundary"])
        self.assertIn("not a temporally prospective test", protocol["claim_boundary"])
        self.assertIn("does not evaluate RL training gains", protocol["claim_boundary"])

    def test_frozen_replay_integrity(self) -> None:
        frozen = json.loads((STUDY / "results/FROZEN_PREDICTION.json").read_text())
        scored = json.loads((STUDY / "results/SCORED_TARGET.json").read_text())
        self.assertFalse(frozen["target"]["outcomes_accessed_before_freeze"])
        self.assertEqual(scored["freeze_sha256"], frozen["freeze_sha256"])
        self.assertEqual(scored["target_attempt_count"], 456)


if __name__ == "__main__":
    unittest.main()
