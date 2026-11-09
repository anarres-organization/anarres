import importlib.util
import math
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
SCRIPT = SCRIPT_DIR / "target_reward_adapter.py"
SPEC = importlib.util.spec_from_file_location("target_reward_adapter", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class TargetRewardAdapterTests(unittest.TestCase):
    def test_terminal_reward_matches_frozen_product(self):
        self.assertAlmostEqual(MODULE.terminal_reward(-8.0, 0.75), 6.0)
        self.assertEqual(MODULE.terminal_reward(1.0, 0.75), 0.0)

    def test_terminal_reward_rejects_nonfinite_inputs(self):
        with self.assertRaises(ValueError):
            MODULE.terminal_reward(math.nan, 0.5)
        with self.assertRaises(ValueError):
            MODULE.terminal_reward(-8.0, math.inf)

    def test_terminal_reward_rejects_invalid_qed(self):
        with self.assertRaises(ValueError):
            MODULE.terminal_reward(-8.0, -0.1)
        with self.assertRaises(ValueError):
            MODULE.terminal_reward(-8.0, 1.1)

    def test_worker_timeout_is_infrastructure_failure(self):
        with (
            patch.object(
                MODULE.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired(["worker"], 0.01),
            ),
            self.assertRaises(MODULE.OracleInfrastructureError),
        ):
            MODULE.run_worker(Path("unused"), "CCO", 0.01)

    def test_batch_requires_positive_worker_count(self):
        with self.assertRaises(ValueError):
            MODULE.score_batch(Path("unused"), [], max_workers=0)

    def test_batch_preserves_order_and_deduplicates_oracle_calls(self):
        def assess(smiles):
            if smiles == "invalid":
                return {
                    "status": "scientific_zero",
                    "reason": "invalid_molecule",
                    "reward": 0.0,
                }
            return {"status": "eligible", "metrics": {"qed": 0.5}}

        def dock(_target, smiles, _timeout):
            return {
                "affinity": -8.0 if smiles == "first" else -6.0,
                "elapsed_seconds": 1.0,
            }

        with (
            patch.object(MODULE, "molecule_assessment", side_effect=assess),
            patch.object(MODULE, "run_worker", side_effect=dock) as worker,
        ):
            results = MODULE.score_batch(
                Path("unused"),
                ["first", "invalid", "second", "first"],
                max_workers=2,
            )

        self.assertEqual(worker.call_count, 2)
        self.assertEqual([result["reward"] for result in results], [4.0, 0.0, 3.0, 4.0])
        self.assertEqual(results[1]["status"], "scientific_zero")


if __name__ == "__main__":
    unittest.main()
