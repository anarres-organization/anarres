import math
import unittest

from ratio_cs import RatioCS


class TestRatioCS(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(RatioCS().interval(0), (0.0, math.inf))

    def test_direction(self):
        cs = RatioCS()
        for _ in range(150):
            cs.update((0.5, 0.9), (0.5, 0.2))
        z = cs.decision()
        self.assertEqual(z["direction"], "b_greater")
        self.assertLessEqual(z["a"][0], 0.5 / 0.9)
        self.assertGreaterEqual(z["b"][1], 2.5)

    def test_equal(self):
        cs = RatioCS()
        for _ in range(150):
            cs.update((0.2, 0.3), (0.4, 0.6))
        self.assertIsNone(cs.decision()["direction"])

    def test_monotonic(self):
        cs = RatioCS()
        for a in ((0.0, 0.1), (0.8, 0.2), (0.3, 0.7)):
            cs.update(a, a)
        grid = [i / 10 for i in range(101)]
        for sign in (1, -1):
            x = [sign * cs.log_e(0, r, sign) for r in grid]
            self.assertTrue(all(a >= b - 1e-12 for a, b in zip(x, x[1:])))

    def test_invalid_atomic(self):
        cs = RatioCS()
        with self.assertRaises(ValueError):
            cs.update((0.2, 0.3), (0.1, 0))
        self.assertEqual(cs.rows, [[], []])


if __name__ == "__main__":
    unittest.main()
