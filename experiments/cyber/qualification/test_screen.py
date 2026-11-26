"""Input and output contract regression tests."""

import unittest

from screen import plan, report
from screening_budget import leader_rate, pcs_exact


class CLITest(unittest.TestCase):
    def test_plan_actual_400(self):
        p = plan(6, 1.2, 0.9, 0.1)
        self.assertAlmostEqual(
            p["pcs_at_400_per_arm"], pcs_exact(leader_rate(1.2, 0.1), 400, 6, 0.1)
        )

    def test_invalid_targets(self):
        for target in (0, 1, 1.1):
            with self.assertRaises(ValueError):
                plan(4, 1.2, target)

    def test_invalid_alpha(self):
        with self.assertRaises(ValueError):
            report([2, 3], 4, 0)

    def test_no_unbiased_claim(self):
        self.assertIn("independent confirmation", report([2, 3], 4)["effect_estimate"])
