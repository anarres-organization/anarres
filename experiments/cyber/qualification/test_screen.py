"""Tests for the screening entry point.

Run from this directory:  python3 -m unittest test_screen
"""

from __future__ import annotations

import unittest

import screen


class ReportTest(unittest.TestCase):
    def test_resolvable_leader_is_reported_as_a_champion(self) -> None:
        answer = screen.report([34, 14, 12, 16, 11, 15, 13, 9, 17, 10], 400)
        self.assertEqual(answer["regime"], "champion")
        self.assertEqual(answer["winner_index"], 0)
        self.assertLess(answer["p_value"], 0.05)

    def test_flat_panel_is_reported_as_homogeneous(self) -> None:
        answer = screen.report([12, 15, 9, 17, 13, 11, 16, 10, 14, 18], 400)
        self.assertEqual(answer["regime"], "homogeneous")
        self.assertLess(answer["reported_density"], answer["raw_density"])

    def test_single_candidate_is_never_a_champion(self) -> None:
        answer = screen.report([20], 400)
        self.assertEqual(answer["regime"], "homogeneous")


class PlanTest(unittest.TestCase):
    def test_plan_matches_the_exact_table(self) -> None:
        answer = screen.plan(10, 1.5, 0.9)
        self.assertEqual(answer["trials_per_arm_needed"], 1010)
        self.assertLess(answer["identification_at_400_per_arm"], 0.9)
        self.assertGreater(answer["identification_with_racing_at_4000"], 0.7)

    def test_plan_marks_the_reachable_case_as_sufficient(self) -> None:
        answer = screen.plan(6, 2.3, 0.9)
        self.assertEqual(answer["advice"], "the published budget suffices")


if __name__ == "__main__":
    unittest.main()
