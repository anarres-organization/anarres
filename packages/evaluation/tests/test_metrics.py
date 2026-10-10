import unittest

from anarres.evaluation import allocation_regret, paired_utility, pass_at_one


class EvaluationMetricTest(unittest.TestCase):
    def test_pass_at_one(self) -> None:
        self.assertEqual(pass_at_one([1, 0, 1, 1]), 0.75)

    def test_paired_utility(self) -> None:
        self.assertEqual(paired_utility([1, 1], [1, 0]), 0.5)

    def test_regret(self) -> None:
        self.assertAlmostEqual(allocation_regret({"a": 0.2, "b": 0.35}, "a"), 0.15)


if __name__ == "__main__":
    unittest.main()
