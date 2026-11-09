import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).parent / "scripts" / "extract_starting_measurements.py"
SPEC = importlib.util.spec_from_file_location("extract_starting_measurements", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class MeasurementExtractionTests(unittest.TestCase):
    def test_merge_overlapping_ring_sets(self):
        merged = MODULE.merge_overlapping_sets([{0, 1}, {1, 2}, {5, 6}])
        self.assertEqual(merged, [{0, 1, 2}, {5, 6}])

    def test_route_features(self):
        trajectory = [
            {"reaction": None, "building_blocks": [{"id": "a"}]},
            {"reaction": "rxn_b", "building_blocks": [{"id": "b"}]},
            {"reaction": "rxn_a", "building_blocks": []},
        ]
        result = MODULE.route_features(trajectory)
        self.assertEqual(result["generated_action_count"], 3)
        self.assertEqual(result["reaction_depth"], 2)
        self.assertEqual(result["reaction_sequence"], ["rxn_b", "rxn_a"])
        self.assertEqual(result["reaction_families"], ["rxn_a", "rxn_b"])
        self.assertEqual(result["building_block_ids"], ["a", "b"])

    def test_build_records_requires_aligned_inputs(self):
        with self.assertRaisesRegex(ValueError, "equal length"):
            MODULE.build_records([], [{}], np.empty((0, 4)), 1)

    def test_record_identity_changes_with_view(self):
        trajectory = [{"reaction": None}]
        first = MODULE.record_id(1, 0, "CC", trajectory)
        second = MODULE.record_id(2, 0, "CC", trajectory)
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
