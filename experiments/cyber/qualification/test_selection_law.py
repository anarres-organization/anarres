"""Regression tests for conditional selection and grouping denominators."""

import itertools
import math
import unittest

from selection_law import advantage_mass, grouping_law, report, winner_p_value


class SelectionTest(unittest.TestCase):
    def test_group_denominators(self):
        for p, g in itertools.product((0.02, 0.035, 0.1, 0.5, 0.9), (2, 8, 16)):
            r = grouping_law(p, g)
            expected = sum(
                math.comb(g, k) * p**k * (1 - p)**(g - k) * advantage_mass(k, g)
                for k in range(g + 1)
            )
            self.assertAlmostEqual(expected / g, r["raw_mass_per_generated_rollout"])
            self.assertAlmostEqual(
                expected / g, r["raw_mass_per_retained_rollout"] * r["mixed_probability"]
            )

    def test_conditional_exact_and_size(self):
        for n, k in itertools.product(range(1, 5), (2, 3)):
            cells = list(itertools.product(range(n + 1), repeat=k))
            for total in range(n * k + 1):
                group = [a for a in cells if sum(a) == total]
                weights = [math.prod(math.comb(n, x) for x in a) for a in group]
                denom = sum(weights)
                rejection = 0
                for a, w in zip(group, weights, strict=True):
                    score = max(x * (n - x) for x in a)
                    truth = sum(
                        v for b, v in zip(group, weights, strict=True)
                        if max(x * (n - x) for x in b) >= score
                    ) / denom
                    p = winner_p_value(list(a), n)
                    self.assertAlmostEqual(p, truth)
                    rejection += w * (p <= 0.05)
                self.assertLessEqual(rejection / denom, 0.05 + 1e-12)

    def test_tied_variance(self):
        r = report([2, 8, 0], 10)
        self.assertEqual(r["winner_indices"], [0, 1])

    def test_one_arm(self):
        self.assertEqual(winner_p_value([2], 10), 1)

    def test_invalid_counts(self):
        for counts, n in (([], 3), ([4], 3), ([-1], 3), ([1.1], 3), ([1], 0)):
            with self.assertRaises(ValueError):
                winner_p_value(counts, n)
