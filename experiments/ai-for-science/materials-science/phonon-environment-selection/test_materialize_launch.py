import importlib.util
import json
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).parent
SCRIPT = ROOT / "scripts" / "materialize_launch.py"
SPEC = importlib.util.spec_from_file_location("materialize_launch", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class LaunchMaterializationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.freeze = json.loads((ROOT / "FREEZE.json").read_text(encoding="utf-8"))
        cls.protocol = json.loads((ROOT / "PROTOCOL.json").read_text(encoding="utf-8"))

    def test_committed_freeze_is_bound_to_protocol(self):
        MODULE.validate_freeze(self.freeze, self.protocol)

    def test_launch_matrix_is_complete(self):
        rows = MODULE.candidate_matrix(self.freeze, self.protocol)
        self.assertEqual(len(rows), 24)
        self.assertEqual(len({row["run_id"] for row in rows}), 24)

    def test_changed_protocol_is_rejected(self):
        edited = deepcopy(self.protocol)
        edited["training"]["epochs"] += 1
        with self.assertRaisesRegex(ValueError, "not bound"):
            MODULE.validate_freeze(self.freeze, edited)

    def test_open_external_labels_are_rejected(self):
        edited = deepcopy(self.freeze)
        edited["external_test_labels_inspected"] = True
        payload = dict(edited)
        payload.pop("freeze_sha256")
        edited["freeze_sha256"] = MODULE.canonical_digest(payload)
        with self.assertRaisesRegex(ValueError, "External labels"):
            MODULE.validate_freeze(edited, self.protocol)


if __name__ == "__main__":
    unittest.main()
