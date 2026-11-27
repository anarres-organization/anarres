"""Independent small-case enumeration and bound regression checks."""

import itertools
import math
import unittest

import information_floor as model


class InformationTest(unittest.TestCase):
    def test_kl_boundaries(self):
        self.assertEqual(model.bernoulli_kl(0, 0), 0)
        self.assertEqual(model.bernoulli_kl(1, 1), 0)
        self.assertAlmostEqual(model.bernoulli_kl(0, 0.3), -math.log(0.7))
        self.assertAlmostEqual(model.bernoulli_kl(1, 0.3), -math.log(0.3))
        self.assertEqual(model.bernoulli_kl(0.3, 0), math.inf)
        self.assertEqual(model.bernoulli_kl(0.3, 1), math.inf)

    def test_small_exact_ties(self):
        for n, k, p, q in itertools.product(range(4), range(2, 5), (0, 0.2, 0.5), (0.5, 0.8, 1)):
            def mass(x, r):
                return math.comb(n, x) * r**x * (1 - r)**(n - x)

            total = 0.0
            for counts in itertools.product(range(n + 1), repeat=k):
                if counts[0] != max(counts):
                    continue
                total += (
                    mass(counts[0], q)
                    * math.prod(mass(x, p) for x in counts[1:])
                    / counts.count(counts[0])
                )
            self.assertAlmostEqual(model.probability_correct(n, p, q, k), total, places=12)

    def test_equal_arms(self):
        for p in (0, 0.035, 0.5, 1):
            self.assertAlmostEqual(model.probability_correct(40, p, p, 10), 0.1)
            self.assertEqual(model.bounds(p, p), (math.inf, math.inf))

    def test_bounds_grid(self):
        for p, q, k, e in itertools.product((0.01, 0.035, 0.2), (0.3, 0.5, 0.8), (2, 5, 10), (0.05, 0.1)):
            lo, hi = model.bounds(p, q, k, e)
            self.assertLessEqual(lo, hi)
            self.assertGreaterEqual(model.probability_correct(hi, p, q, k) + 1e-12, 1 - e)
            self.assertLess(model.probability_correct(lo - 1, p, q, k), 1 - e + 1e-12)

    def test_counterexample_regression(self):
        for ratio, n in ((2.3, 289), (3, 142)):
            p = 0.035
            self.assertGreaterEqual(model.probability_correct(n, p, p * ratio), 0.95)
            self.assertLessEqual(model.bounds(p, p * ratio)[0], n)

    def test_shared_corruption(self):
        p, q = 0.035, 0.0805
        for fn, fp in ((0.38, 0), (0, 0.10)):
            a, b = [model.observed_rate(x, fn, fp) for x in (p, q)]
            self.assertLess(a, b)
            self.assertLess(model.bernoulli_kl(a, b), model.bernoulli_kl(p, q))

    def test_extreme_perfect_separation(self):
        self.assertEqual(model.bounds(0, 1), (1, 1))
        self.assertEqual(model.probability_correct(1, 0, 1), 1)


if __name__ == "__main__":
    unittest.main()
