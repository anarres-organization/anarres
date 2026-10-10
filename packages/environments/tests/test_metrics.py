import unittest

from anarres.environments.metrics import GroupMeasurement, compute_coordinates
from anarres.environments.qualification import Qualification, qualify_group


class EnvironmentMetricTest(unittest.TestCase):
    def test_coordinates(self) -> None:
        coordinates = compute_coordinates(
            [
                GroupMeasurement("a", 2.0, 100),
                GroupMeasurement("b", 1.0, 200),
            ]
        )
        self.assertEqual(coordinates.rho_per_million_tokens, 10_000.0)
        self.assertAlmostEqual(coordinates.effective_coverage, 0.9)

    def test_zero_mass_has_zero_coverage(self) -> None:
        coordinates = compute_coordinates([GroupMeasurement("a", 0.0, 10)])
        self.assertEqual(coordinates.effective_coverage, 0.0)

    def test_infrastructure_failure_is_not_scientific_zero(self) -> None:
        result = qualify_group(
            oracle_passed=True,
            noop_passed=False,
            infrastructure_valid=False,
            rewards=[0.0, 1.0],
        )
        self.assertEqual(result.status, Qualification.REPAIR)


if __name__ == "__main__":
    unittest.main()
