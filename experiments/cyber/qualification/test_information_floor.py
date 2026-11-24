"""Tests for the information floor.

Run from this directory:  python3 -m unittest test_information_floor
"""

from __future__ import annotations

import unittest

import information_floor as floor


class DivergenceTest(unittest.TestCase):
    def test_identical_arms_carry_no_information(self) -> None:
        self.assertEqual(floor.divergence(0.035, 1.0), 0.0)

    def test_divergence_grows_with_the_ratio(self) -> None:
        values = [floor.divergence(0.035, ratio) for ratio in (1.2, 1.5, 2.3, 3.0)]
        self.assertEqual(values, sorted(values))

    def test_dense_ratios_carry_more_information_than_sparse_ones(self) -> None:
        self.assertGreater(floor.divergence(0.4, 2.0), floor.divergence(0.035, 2.0))


class FloorTest(unittest.TestCase):
    def test_floor_falls_as_the_ratio_grows(self) -> None:
        self.assertGreater(
            floor.floor_rollouts(0.035, 1.5, 10), floor.floor_rollouts(0.035, 2.3, 10)
        )

    def test_floor_rises_with_more_candidates(self) -> None:
        self.assertGreater(
            floor.floor_rollouts(0.035, 2.3, 20), floor.floor_rollouts(0.035, 2.3, 5)
        )

    def test_one_and_a_half_times_needs_about_fifteen_hundred_rollouts(self) -> None:
        self.assertAlmostEqual(floor.floor_rollouts(0.035, 1.5, 10), 1527, delta=10)

    def test_two_point_three_times_needs_about_three_hundred_rollouts(self) -> None:
        self.assertAlmostEqual(floor.floor_rollouts(0.035, 2.3, 10), 304, delta=5)


class CrossCheckTest(unittest.TestCase):
    def test_the_exact_screen_sits_within_ten_percent_of_the_floor(self) -> None:
        panel = floor.released_panel()
        self.assertAlmostEqual(
            panel["ratio_1_5_floor"] / panel["ratio_1_5_screen"], 0.95, delta=0.06
        )

    def test_the_sequential_design_sits_on_the_floor(self) -> None:
        panel = floor.released_panel()
        self.assertAlmostEqual(
            panel["ratio_2_3_sequential"] / panel["ratio_2_3_floor"], 1.02, delta=0.06
        )


class VerifierTest(unittest.TestCase):
    def test_a_false_negative_rate_costs_rollouts(self) -> None:
        multiplier = floor.verifier_multiplier(0.035, 2.3, 0.38)
        self.assertGreater(multiplier, 1.6)

    def test_a_false_positive_rate_dilutes_the_divergence_while_raising_the_rate(self) -> None:
        clean = floor.divergence(0.035, 2.3)
        dirty = floor.divergence(0.035, 2.3, false_positive=0.10)
        self.assertLess(dirty, clean)
        self.assertGreater(floor.observed_rate(0.035, false_positive=0.10), 0.035)
        self.assertAlmostEqual(floor.corruption_multiplier(0.035, 2.3, 0.10), 2.77, delta=0.05)


class RatioTest(unittest.TestCase):
    def test_four_hundred_rollouts_resolve_about_two_times(self) -> None:
        self.assertAlmostEqual(floor.smallest_ratio(0.035, 400, 10), 2.10, delta=0.05)


if __name__ == "__main__":
    unittest.main()
