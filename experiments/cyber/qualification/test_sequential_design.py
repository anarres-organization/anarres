"""Tests for the early-stopping comparison design.

Run from this directory:  python3 -m unittest test_sequential_design
"""

from __future__ import annotations

import unittest

import environment_ranking as ranking
import sequential_design as design


class ClosedFormTest(unittest.TestCase):
    def test_closed_form_matches_the_profiled_optimiser(self) -> None:
        import numpy as np

        cases = [(12, 46, 400), (40, 360, 400), (5, 9, 160), (0, 6, 160), (3, 3, 60)]
        for a, b, n in cases:
            closed = float(design.profile_lr(np.array([[a]]), np.array([[b]]), float(n))[0, 0])
            fitted = ranking.compare(a, n, b, n).likelihood_ratio
            self.assertAlmostEqual(closed, fitted, places=6)

    def test_density_inverse_recovers_the_lower_rate(self) -> None:
        for p in (0.02, 0.035, 0.2, 0.45):
            self.assertAlmostEqual(design.phi(p), design.phi(1 - p), places=12)
            self.assertAlmostEqual(design.p_from_phi(design.phi(p)), p, places=10)


class ExactnessTest(unittest.TestCase):
    def test_single_look_matches_the_fixed_sample_power(self) -> None:
        result = design.evaluate(0.035, 0.085, design.CRITICAL, None, trials=80, looks=(80,))
        self.assertAlmostEqual(
            result["rejection_probability"], design.fixed_power(0.035, 0.085, 80), places=9
        )
        self.assertAlmostEqual(result["expected_trials"], 80.0, places=9)

    def test_futility_shortens_the_null_without_touching_the_size(self) -> None:
        plain = design.evaluate(
            0.035, 0.035, design.CRITICAL, None, trials=120, looks=(40, 80, 120)
        )
        stopping = design.evaluate(
            0.035, 0.035, design.CRITICAL, 1.0, trials=120, looks=(40, 80, 120)
        )
        self.assertLess(stopping["expected_trials"], plain["expected_trials"])
        # Stopping for futility can only remove later rejections, so the size falls a
        # little; it must never rise.
        self.assertLessEqual(stopping["rejection_probability"], plain["rejection_probability"])
        self.assertGreater(stopping["rejection_probability"], plain["rejection_probability"] - 0.01)


if __name__ == "__main__":
    unittest.main()
