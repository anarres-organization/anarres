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


if __name__ == "__main__":
    unittest.main()
