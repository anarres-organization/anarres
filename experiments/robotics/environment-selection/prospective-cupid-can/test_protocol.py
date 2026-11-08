import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "validate_protocol", ROOT / "scripts" / "validate_protocol.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
validate = MODULE.validate


class ProtocolTest(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads((ROOT / "PROTOCOL.json").read_text())

    def test_contract_is_consistent(self):
        validate(self.protocol)

    def test_outcome_lock_precedes_training(self):
        stages = self.protocol["chronology"]
        self.assertIn("serialize candidate memberships", stages["stage_3"])
        self.assertIn("train and evaluate", stages["stage_4"])
        self.assertIn("open outcomes", stages["stage_5"])

    def test_training_seed_is_primary_unit(self):
        self.assertEqual(self.protocol["evaluation"]["primary_unit"], "training_seed")


if __name__ == "__main__":
    unittest.main()
