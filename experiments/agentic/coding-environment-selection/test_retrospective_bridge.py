from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "bridge", ROOT / "scripts" / "reproduce_retrospective_bridge.py"
)
assert SPEC and SPEC.loader
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)


class RetrospectiveBridgeTest(unittest.TestCase):
    def test_summary_reproduces(self) -> None:
        self.assertEqual(
            BRIDGE.compute(),
            json.loads((ROOT / "results" / "retrospective-bridge-summary.json").read_text()),
        )

    def test_units_and_baseline_are_preserved(self) -> None:
        summary = BRIDGE.compute()
        self.assertEqual(summary["sources"], 7)
        self.assertEqual(summary["independent_training_decisions"], 14)
        self.assertEqual(summary["endpoint_panels"], 27)
        self.assertGreater(
            summary["practical_measurement_rule"]["pairwise_ordering"],
            summary["uninformed_tie"]["pairwise_ordering"],
        )
        self.assertLess(
            summary["practical_measurement_rule"]["mean_normalized_regret"],
            summary["uninformed_tie"]["mean_normalized_regret"],
        )


if __name__ == "__main__":
    unittest.main()
