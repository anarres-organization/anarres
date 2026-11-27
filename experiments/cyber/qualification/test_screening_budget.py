"""Independent enumeration and racing regression checks."""

import itertools
import math
import unittest

from screening_budget import leader_rate, pcs_exact, racing_pcs


class BudgetTest(unittest.TestCase):
    def test_exact_ties_exhaustive(self):
        for n, k, p, q in itertools.product(range(1, 5), (2, 3), (0.1, 0.4, 0.7), (0.3, 0.5, 0.6)):
            if q * (1 - q) + 1e-15 < p * (1 - p):
                continue

            def mass(x, r):
                return math.comb(n, x) * r**x * (1 - r)**(n - x)

            truth = 0
            for counts in itertools.product(range(n + 1), repeat=k):
                s = [x * (n - x) for x in counts]
                if s[0] == max(s):
                    truth += (
                        mass(counts[0], q)
                        * math.prod(mass(x, p) for x in counts[1:])
                        / s.count(s[0])
                    )
            self.assertAlmostEqual(pcs_exact(q, n, k, p), truth)

    def test_mirrored_rates_tie(self):
        self.assertAlmostEqual(pcs_exact(0.9, 80, 5, 0.1), 0.2)

    def test_ratio_exact(self):
        for p in (0.035, 0.8):
            q = leader_rate(1.2, p)
            self.assertAlmostEqual(q * (1 - q) / (p * (1 - p)), 1.2)

    def test_racing_single_round(self):
        result = racing_pcs(1.5, 6, 6, 1, replicates=10000, total=1200, baseline=0.035)
        self.assertAlmostEqual(
            result["pcs"], pcs_exact(leader_rate(1.5, 0.035), 200, 6), delta=0.02
        )
        self.assertEqual(result["spent"], 1200)

    def test_impossible(self):
        for ratio, p in ((2, 0.49), (1, 0.1), (1.5, 0)):
            with self.assertRaises(ValueError):
                leader_rate(ratio, p)
