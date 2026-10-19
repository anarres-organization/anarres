import importlib.util
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "experiments"
    / "cyber"
    / "qualification"
    / "power_analysis.py"
)
SPEC = importlib.util.spec_from_file_location("cyber_power_analysis", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CyberPowerAnalysisTest(unittest.TestCase):
    def test_frozen_task_counts(self) -> None:
        self.assertEqual(MODULE.required_tasks(0.08, 0.20), 246)
        self.assertEqual(MODULE.required_tasks(0.06, 0.20), 437)

    def test_detectable_effect(self) -> None:
        self.assertAlmostEqual(MODULE.detectable_effect(256, 0.20), 0.0783067, places=6)

    def test_invalid_inputs(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.required_tasks(0, 0.20)
        with self.assertRaises(ValueError):
            MODULE.detectable_effect(0, 0.20)


if __name__ == "__main__":
    unittest.main()
