"""Regression tests preventing pseudoreplication across training seeds."""

import unittest

from resolution_plan import analyse, validate_design


def rows():
    return [
        {
            "seed": str(i), "control_run_id": f"c{i}", "treatment_run_id": f"t{i}",
            "panel_sha256": "a" * 64, "n_items": "300", "correct_control": "150",
            "correct_treatment": str(150 + i - 4),
        }
        for i in range(9)
    ]


class RunLevelTest(unittest.TestCase):
    def test_mean_and_unit(self):
        result = analyse(rows())
        self.assertEqual(result["n_pairs"], 9)
        self.assertAlmostEqual(result["mean_pp"], 0)
        self.assertGreater(result["between_pair_sd_pp"], 0)
        self.assertEqual(result["secondary_sign_p"], 1)
        self.assertIsNone(result["power_claim"])

    def test_item_replication_rejected(self):
        with self.assertRaises(ValueError):
            analyse(rows() * 300)

    def test_duplicate_seed_rejected(self):
        data = rows()
        data[8]["seed"] = data[0]["seed"]
        with self.assertRaises(ValueError):
            analyse(data)

    def test_reused_training_run_rejected(self):
        data = rows()
        data[8]["treatment_run_id"] = data[0]["control_run_id"]
        with self.assertRaises(ValueError):
            analyse(data)

    def test_different_panel_rejected(self):
        data = rows()
        data[8]["panel_sha256"] = "b" * 64
        with self.assertRaises(ValueError):
            analyse(data)

    def test_pooled_counts_rejected(self):
        data = rows()
        data[0]["n_items"] = "2700"
        with self.assertRaises(ValueError):
            analyse(data)

    def test_zero_variance_no_spurious_interval(self):
        data = rows()
        for r in data:
            r["correct_treatment"] = "150"
        self.assertIsNone(analyse(data)["approximate_t95_pp"])

    def test_old_power_claim_rejected(self):
        with self.assertRaises(ValueError):
            validate_design({"analysis_unit": "item", "target_power": .8})


if __name__ == "__main__":
    unittest.main()
