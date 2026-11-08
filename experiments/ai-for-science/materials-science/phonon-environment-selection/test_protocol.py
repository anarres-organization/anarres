import importlib.util
import json
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).parent
SPEC = importlib.util.spec_from_file_location(
    "validate_protocol", ROOT / "scripts" / "validate_protocol.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ProtocolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = json.loads((ROOT / "PROTOCOL.json").read_text(encoding="utf-8"))

    def test_committed_protocol_validates(self):
        self.assertEqual(MODULE.validate(self.protocol), [])

    def test_opening_external_labels_fails(self):
        edited = deepcopy(self.protocol)
        edited["sealed_boundary"]["external_test_labels_inspected_for_this_study"] = True
        self.assertIn("external test labels must remain sealed", MODULE.validate(edited))

    def test_candidate_set_is_fixed(self):
        edited = deepcopy(self.protocol)
        edited["candidate_construction"]["candidate_names"].append("post_hoc")
        self.assertTrue(any("candidate names differ" in error for error in MODULE.validate(edited)))

    def test_atom_strata_must_be_contiguous(self):
        edited = deepcopy(self.protocol)
        edited["candidate_construction"]["atom_count_strata"][1][0] = 13
        self.assertIn("atom-count strata must be contiguous", MODULE.validate(edited))


if __name__ == "__main__":
    unittest.main()
