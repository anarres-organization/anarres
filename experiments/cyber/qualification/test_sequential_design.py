"""Full composite-null and stopping-contract regression tests."""

import unittest

from environment_ranking import fixed_power
from sequential_design import decision, evaluate, thresholds


class SequentialTest(unittest.TestCase):
    def test_single_look(self):
        got = evaluate(0.1, 0.4, (30,))
        self.assertAlmostEqual(got["rejection_probability"], fixed_power(0.1, 0.4, 30))
        self.assertAlmostEqual(got["expected_trials_per_arm"], 30)

    def test_composite_null_grid(self):
        for p in (0, 0.035, 0.1, 0.25, 0.5, 0.75, 0.95, 1):
            for q in (p, 1 - p):
                got = evaluate(p, q, (10, 20, 30))
                self.assertLessEqual(got["rejection_probability"], 0.05 + 1e-12)
                self.assertAlmostEqual(got["mass_check"], 1)

    def test_prespecified_looks(self):
        for looks in ((), (10, 10), (20, 10), (0, 10)):
            with self.assertRaises(ValueError):
                thresholds(looks)

    def test_invalid_increments(self):
        with self.assertRaises(ValueError):
            decision([(1, 1), (0, 2)], (10, 20))

    def test_no_rejection_not_equality(self):
        self.assertEqual(decision([(0, 0)], (10, 20))["status"], "continue")
        self.assertEqual(decision([(0, 0), (0, 0)], (10, 20))["status"], "not_reject")
