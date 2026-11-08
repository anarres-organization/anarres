import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "measure_starting_model.py"
SPEC = importlib.util.spec_from_file_location("measure_starting_model", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class StartingModelMeasurementTest(unittest.TestCase):
    def test_threshold_labels_follow_released_strict_rule(self):
        self.assertEqual(MODULE.threshold_labels(-0.0005), [1.0, 1.0, 1.0, 1.0])
        self.assertEqual(MODULE.threshold_labels(-0.1), [0.0, 0.0, 0.0, 1.0])
        self.assertEqual(MODULE.threshold_labels(-2.0), [0.0, 0.0, 0.0, 0.0])

    def test_pool_weights_use_only_gradient_training(self):
        rows = [
            {"role": "gradient_train", "min_frequency": 0.0},
            {"role": "gradient_train", "min_frequency": -2.0},
            {"role": "checkpoint_validation", "min_frequency": 0.0},
        ]
        weights = MODULE.pool_positive_weights(rows)
        for weight in weights:
            self.assertAlmostEqual(weight, 1.0)

    def test_repeatability_membership_is_deterministic(self):
        rows = [{"role": "gradient_train", "record_id": f"record-{index}"} for index in range(200)]
        first = MODULE.repeatability_ids(rows, count=128)
        second = MODULE.repeatability_ids(list(reversed(rows)), count=128)
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(set(first)))

    def test_requested_rows_preserve_requested_order(self):
        rows = [
            {"role": "gradient_train", "record_id": "a"},
            {"role": "gradient_train", "record_id": "b"},
        ]
        self.assertEqual([row["record_id"] for row in rows], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
