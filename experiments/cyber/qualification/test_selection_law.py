"""Tests for the grouping and selection laws.

Run from this directory:  python3 -m unittest test_selection_law
"""

from __future__ import annotations

import unittest

import numpy as np

import selection_law as law


class GroupingLawTest(unittest.TestCase):
    def test_per_rollout_mass_equals_the_ceiling(self) -> None:
        for p in (0.02, 0.035, 0.1, 0.3):
            for group in (2, 8, 16):
                result = law.grouping_law(p, group)
                self.assertAlmostEqual(result["per_rollout"], result["ceiling"], places=12)

    def test_filtering_costs_exactly_the_coverage(self) -> None:
        result = law.grouping_law(0.035, 8)
        self.assertAlmostEqual(
            result["filtered_per_token"], result["per_rollout"] * result["coverage"], places=12
        )
        self.assertLess(result["filtered_per_token"], 0.3 * result["per_rollout"])


class SelectionLawTest(unittest.TestCase):
    def test_panel_maximum_is_inflated_and_grows_with_candidates(self) -> None:
        small = law.expected_max(0.035, 5)
        large = law.expected_max(0.035, 20)
        self.assertGreater(small, law.phi(0.035))
        self.assertGreater(large, small)

    def test_inversion_recovers_a_rate(self) -> None:
        for p in (0.06, 0.09):
            value = law.expected_max(p, 10)
            self.assertAlmostEqual(law.invert_max(value, 10), p, delta=0.004)

    def test_null_panel_lands_in_the_homogeneous_regime(self) -> None:
        counts = np.array([12, 15, 9, 17, 13, 11, 16, 10, 14, 18])
        answer = law.report(counts)
        self.assertEqual(answer["regime"], "homogeneous")
        self.assertLess(answer["corrected"], answer["raw"])

    def test_resolvable_leader_is_certified(self) -> None:
        counts = np.array([34, 14, 12, 16, 11, 15, 13, 9, 17, 10])
        answer = law.report(counts)
        self.assertEqual(answer["regime"], "champion")
        self.assertAlmostEqual(answer["corrected"], answer["raw"], places=12)

    def test_claim_rate_holds_on_a_null_panel(self) -> None:
        generator = np.random.default_rng(11)
        counts = generator.binomial(400, 0.035, size=(700, 10))
        claims = np.mean([law.report(counts[i])["regime"] == "champion" for i in range(700)])
        self.assertGreater(claims, 0.01)
        self.assertLess(claims, 0.11)


if __name__ == "__main__":
    unittest.main()
