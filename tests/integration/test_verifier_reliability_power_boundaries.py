"""Exact McNemar power edge cases for the released verifier reliability pilot."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT / "experiments/mathematics/verifier-reliability-pilot"
    / "scripts/detectable_difference.py"
)
SPEC = importlib.util.spec_from_file_location("anarres_verifier_power", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
POWER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POWER)


class ExactPowerBoundaryTest(unittest.TestCase):
    def test_six_unanimous_discordances_reject_with_unit_power(self) -> None:
        # 6 of 6 discordances in one direction: exact two-sided p = 2 / 64.
        self.assertAlmostEqual(POWER.exact_two_sided(6, 0), 0.03125)
        self.assertAlmostEqual(POWER.power(6, 300, 2.0), 1.0)

    def test_five_unanimous_discordances_do_not_reject(self) -> None:
        # Even a point mass cannot reject at alpha .05 when m=5.
        self.assertAlmostEqual(POWER.exact_two_sided(5, 0), 0.0625)
        self.assertAlmostEqual(POWER.power(5, 100, 5.0), 0.0)

    def test_sparse_discordance_minimum_detectable_is_finite(self) -> None:
        resolution, attained = POWER.minimum_detectable(6, 300)
        self.assertAlmostEqual(resolution, 2.0)
        self.assertAlmostEqual(attained, 1.0)

    def test_insufficient_discordance_reports_unattainable_power(self) -> None:
        resolution, attained = POWER.minimum_detectable(5, 100)
        self.assertEqual(resolution, float("inf"))
        self.assertEqual(attained, 0.0)

    def test_zero_discordances_cannot_power_a_rejection(self) -> None:
        self.assertEqual(POWER.power(0, 300, 0.0), 0.0)
        self.assertEqual(POWER.minimum_detectable(0, 300), (float("inf"), 0.0))


if __name__ == "__main__":
    unittest.main()
