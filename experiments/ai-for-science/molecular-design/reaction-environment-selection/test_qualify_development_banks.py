import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
SCRIPT = SCRIPT_DIR / "qualify_development_banks.py"
SPEC = importlib.util.spec_from_file_location("qualify_development_banks", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class BankConfirmationTests(unittest.TestCase):
    def test_spearman_identical_order(self):
        value, status = MODULE.spearman([1, 2, 3], [2, 4, 6])
        self.assertAlmostEqual(value, 1.0)
        self.assertEqual(status, "finite")

    def test_spearman_reversed_order(self):
        value, _ = MODULE.spearman([1, 2, 3], [6, 4, 2])
        self.assertAlmostEqual(value, -1.0)

    def test_constants_follow_frozen_rule(self):
        self.assertEqual(MODULE.spearman([1, 1], [2, 2]), (1.0, "constant_in_both_views"))
        self.assertEqual(MODULE.spearman([1, 1], [1, 2]), (0.0, "constant_in_one_view"))

    def test_average_ranks_handles_ties(self):
        self.assertEqual(MODULE.average_ranks([1, 1, 3]).tolist(), [1.5, 1.5, 3.0])

    def test_view_seeds_must_bind_to_qualified_construction_view(self):
        measurement = {"sampling": {"construction_view_seed": 22}}
        bank = {"confirmation_rule": {"construction_view_seed": 22, "confirmation_view_seed": 24}}
        self.assertEqual(MODULE.expected_view_seeds(measurement, bank), [22, 24])
        bank["confirmation_rule"]["construction_view_seed"] = 20
        with self.assertRaisesRegex(ValueError, "does not match"):
            MODULE.expected_view_seeds(measurement, bank)

    def test_result_schema_tracks_bank_contract_revision(self):
        self.assertEqual(MODULE.result_schema_version({"schema_version": "2.0"}), "2.0")
        with self.assertRaisesRegex(ValueError, "required"):
            MODULE.result_schema_version({})

    def test_selector_fidelity_uses_strict_directional_contrasts(self):
        summaries = {
            "hash_uniform": {"reward": 1.0, "cost": 4.0},
            "reward_signal": {"reward": 2.0, "cost": 4.0},
            "validity_cost": {"reward": 1.0, "cost": 3.0},
        }
        checks = [
            {
                "check_id": "reward",
                "bank": "reward_signal",
                "reference_bank": "hash_uniform",
                "coordinate": "reward",
                "direction": "higher",
            },
            {
                "check_id": "cost",
                "bank": "validity_cost",
                "reference_bank": "hash_uniform",
                "coordinate": "cost",
                "direction": "lower",
            },
        ]
        self.assertEqual(
            MODULE.selector_fidelity_checks(summaries, checks),
            {"reward": True, "cost": True},
        )
        summaries["reward_signal"]["reward"] = 1.0
        self.assertFalse(MODULE.selector_fidelity_checks(summaries, checks)["reward"])

    def test_selector_fidelity_rejects_unknown_direction(self):
        summaries = {"a": {"x": 1.0}, "b": {"x": 2.0}}
        checks = [
            {
                "check_id": "bad",
                "bank": "a",
                "reference_bank": "b",
                "coordinate": "x",
                "direction": "sideways",
            }
        ]
        with self.assertRaisesRegex(ValueError, "unsupported"):
            MODULE.selector_fidelity_checks(summaries, checks)


if __name__ == "__main__":
    unittest.main()
