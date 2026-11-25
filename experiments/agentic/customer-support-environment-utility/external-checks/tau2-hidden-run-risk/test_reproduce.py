import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

STUDY = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "tau2_hidden_run_reproduce", STUDY / "scripts/reproduce.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load reproducer")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


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

    def test_manifest_detects_changed_release_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            release = Path(directory) / "release"
            shutil.copytree(STUDY, release, ignore=shutil.ignore_patterns("__pycache__"))
            MODULE.verify_manifest(release)
            scored = release / "results/SCORED_TARGET.json"
            scored.write_text(scored.read_text() + "\n")
            with self.assertRaisesRegex(AssertionError, "MANIFEST"):
                MODULE.verify_manifest(release)

    def test_development_receipts_do_not_repeat_simulator_prompt(self) -> None:
        development = json.loads((STUDY / "results/DEVELOPMENT_AUDIT.json").read_text())
        for source in development["source"]["files"]:
            self.assertNotIn("global_simulation_guidelines", source["reported_user"])


if __name__ == "__main__":
    unittest.main()
