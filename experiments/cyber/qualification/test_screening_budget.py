"""Tests for the screening budget analysis.

Run from this directory:  python3 -m unittest test_screening_budget
"""

from __future__ import annotations

import unittest

import screening_budget as budget


class ExactTest(unittest.TestCase):
    def test_identification_probability_rises_with_trials(self) -> None:
        self.assertLess(
            budget.pcs_exact(budget.LEADERS[1.5], 400, 10),
            budget.pcs_exact(budget.LEADERS[1.5], 700, 10),
        )

    def test_four_times_the_budget_certifies_one_point_five(self) -> None:
        self.assertGreater(budget.pcs_exact(budget.LEADERS[1.5], 1600, 10), 0.95)

    def test_trials_for_target_is_the_smallest_count(self) -> None:
        target = 0.90
        trials = budget.trials_for_pcs(target, budget.LEADERS[1.5], 10)
        self.assertGreaterEqual(budget.pcs_exact(budget.LEADERS[1.5], trials, 10), target)
        self.assertLess(budget.pcs_exact(budget.LEADERS[1.5], trials - 1, 10), target)


class RacingTest(unittest.TestCase):
    def test_single_round_racing_reproduces_the_exact_answer(self) -> None:
        answer = budget.racing_pcs(
            ratio=2.3, candidates=6, keep=6, pilot_fraction=1.0, replicates=1500, total=1200
        )
        self.assertAlmostEqual(answer, budget.pcs_exact(budget.LEADERS[2.3], 200, 6), delta=0.04)

    def test_two_stage_beats_the_even_split_at_the_margin(self) -> None:
        even = budget.even_split_pcs(1.5, 10)
        racing = budget.racing_pcs(1.5, 10, 4, 0.5)
        self.assertGreater(racing - even, 0.05)


if __name__ == "__main__":
    unittest.main()
