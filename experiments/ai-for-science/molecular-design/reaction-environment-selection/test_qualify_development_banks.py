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


if __name__ == "__main__":
    unittest.main()
