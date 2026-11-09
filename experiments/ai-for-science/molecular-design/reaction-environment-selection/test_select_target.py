import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "select_target.py"
SPEC = importlib.util.spec_from_file_location("select_target", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SelectTargetTests(unittest.TestCase):
    def test_hash_rank_is_deterministic(self):
        self.assertEqual(MODULE.hash_rank("P08254"), MODULE.hash_rank("P08254"))
        self.assertNotEqual(MODULE.hash_rank("P08254"), MODULE.hash_rank("P00533"))

    def test_file_sha256(self):
        expected = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.bin"
            path.write_bytes(b"abc")
            self.assertEqual(MODULE.file_sha256(path), expected)

    def test_summary_detects_incomplete_view(self):
        rows = [{"status": "ok", "reward": 1.0, "oracle_elapsed_seconds": 2.0}]
        summary = MODULE.summarize_view(rows, 2)
        self.assertFalse(summary["complete"])
        self.assertEqual(summary["eligible_fraction"], 0.5)
        self.assertEqual(summary["oracle_completion_fraction"], 0.0)

    def test_empty_views_fail_without_raising(self):
        contract = {
            "sampling": {"trajectory_attempts_per_view": 4},
            "per_target_gates": {
                "minimum_returned_valid_fraction_per_view": 0.875,
                "minimum_unique_fraction_per_view": 0.75,
                "minimum_reward_eligible_fraction_per_view": 0.5,
                "minimum_oracle_completion_fraction_per_view": 0.95,
                "minimum_positive_reward_fraction_per_view": 0.5,
                "minimum_pooled_reward_p90_minus_p10": 0.5,
                "maximum_absolute_view_median_reward_difference": 0.75,
                "maximum_absolute_view_positive_fraction_difference": 0.15,
                "maximum_median_oracle_seconds": 30.0,
                "maximum_p95_oracle_seconds": 120.0,
            },
        }
        starting = {
            "views": [
                {"attempts": 4, "returned_valid": 4, "unique_smiles": 4},
                {"attempts": 4, "returned_valid": 4, "unique_smiles": 4},
            ]
        }
        result = MODULE.apply_target_gates("P08254", [[], []], contract, starting, True)
        self.assertEqual(result["qualification"], "fail")
        self.assertIsNone(result["pooled_reward_p90_minus_p10"])

    def test_gates_pass_a_well_behaved_target(self):
        contract = {
            "sampling": {"trajectory_attempts_per_view": 4},
            "per_target_gates": {
                "minimum_returned_valid_fraction_per_view": 0.875,
                "minimum_unique_fraction_per_view": 0.75,
                "minimum_reward_eligible_fraction_per_view": 0.5,
                "minimum_oracle_completion_fraction_per_view": 0.95,
                "minimum_positive_reward_fraction_per_view": 0.5,
                "minimum_pooled_reward_p90_minus_p10": 0.5,
                "maximum_absolute_view_median_reward_difference": 0.75,
                "maximum_absolute_view_positive_fraction_difference": 0.15,
                "maximum_median_oracle_seconds": 30.0,
                "maximum_p95_oracle_seconds": 120.0,
            },
        }
        starting = {
            "views": [
                {"attempts": 4, "returned_valid": 4, "unique_smiles": 4},
                {"attempts": 4, "returned_valid": 4, "unique_smiles": 4},
            ]
        }
        first = [
            {"status": "ok", "reward": reward, "oracle_elapsed_seconds": 2.0}
            for reward in (1.0, 2.0, 3.0, 4.0)
        ]
        second = [
            {"status": "ok", "reward": reward, "oracle_elapsed_seconds": 3.0}
            for reward in (1.1, 2.1, 3.1, 4.1)
        ]
        result = MODULE.apply_target_gates("P08254", [first, second], contract, starting, True)
        self.assertEqual(result["qualification"], "pass")
        self.assertTrue(all(result["checks"].values()))


if __name__ == "__main__":
    unittest.main()
