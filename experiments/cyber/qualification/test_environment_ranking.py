"""Exact conditional and task-pair regression tests."""

import itertools
import math
import unittest
from fractions import Fraction

from environment_ranking import compare, equality_p, fixed_power, invert_channel, observed_rate, variance_p
from paired_design import paired_summary


class ComparisonTest(unittest.TestCase):
    def test_exact_conditional_tail(self):
        for na, nb in itertools.product(range(1, 6), repeat=2):
            for a, b in itertools.product(range(na + 1), range(nb + 1)):
                t = a + b
                w = math.comb(na, a) * math.comb(nb, b)
                weights = [
                    math.comb(na, k) * math.comb(nb, t - k)
                    for k in range(max(0, t - nb), min(na, t) + 1)
                ]
                self.assertEqual(
                    equality_p(a, na, b, nb),
                    Fraction(sum(v for v in weights if v <= w), sum(weights)),
                )

    def test_full_null_grid(self):
        for p in (0, 0.035, 0.1, 0.25, 0.5, 0.75, 0.95, 1):
            for q in (p, 1 - p):
                self.assertLessEqual(fixed_power(p, q, 30), 0.05 + 1e-12)

    def test_mirror(self):
        self.assertEqual(variance_p(40, 400, 360, 400), 1)
        self.assertTrue(compare(12, 400, 46, 400)["reject"])

    def test_known_channel(self):
        for p in (0, 0.035, 0.5, 0.9, 1):
            self.assertAlmostEqual(invert_channel(observed_rate(p, 0.38, 0.05), 0.38, 0.05), p)

    def test_invalid(self):
        for a, n, b, m in ((2, 1, 0, 1), (-1, 2, 0, 2), (0, 0, 1, 2)):
            with self.assertRaises(ValueError):
                variance_p(a, n, b, m)

    def test_paired_task_signflip(self):
        rows = [("a", 0, 2), ("b", 1, 2), ("c", 2, 2), ("d", 3, 0)]
        got = paired_summary(rows, 8)
        d = [b * (8 - b) - a * (8 - a) for _, a, b in rows]
        expected = sum(
            abs(sum(v * s for v, s in zip(d, signs, strict=True))) >= abs(sum(d))
            for signs in itertools.product((-1, 1), repeat=4)
        ) / 16
        self.assertEqual(got["exchangeability_p"], expected)
        self.assertEqual(got["task_pairs"], 4)

    def test_duplicate_task(self):
        with self.assertRaises(ValueError):
            paired_summary([("a", 0, 1), ("a", 0, 1)], 8)
