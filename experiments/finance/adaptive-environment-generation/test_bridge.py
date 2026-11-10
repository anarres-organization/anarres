"""Integrity checks for the adaptive finance environment bridge."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "score_bridge.py"


class AdaptiveEnvironmentBridgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        specification = importlib.util.spec_from_file_location("adaptive_bridge", SCRIPT)
        cls.module = importlib.util.module_from_spec(specification)
        assert specification.loader is not None
        specification.loader.exec_module(cls.module)
        cls.data = json.loads((ROOT / "data" / "panels.json").read_text())
        cls.result = json.loads((ROOT / "results" / "summary.json").read_text())

    def test_support_and_unique_identities(self) -> None:
        self.assertEqual(self.result["support"], {"sources": 5, "panels": 17, "arms": 53})
        panel_ids = [panel["panel_id"] for panel in self.data["panels"]]
        self.assertEqual(len(panel_ids), len(set(panel_ids)))
        for panel in self.data["panels"]:
            arm_ids = [arm["id"] for arm in panel["arms"]]
            self.assertEqual(len(arm_ids), len(set(arm_ids)))
            self.assertIn(panel["baseline"], arm_ids)

    def test_feature_shapes(self) -> None:
        width = len(self.data["feature_names"])
        for panel in self.data["panels"]:
            for arm in panel["arms"]:
                self.assertEqual(len(arm["features"]), width)
                self.assertTrue(all(0 <= value <= 1 for value in arm["features"]))

    def test_bridge_beats_always_update(self) -> None:
        practical = self.result["evaluations"]["fixed_practical_rule"]
        update = self.result["evaluations"]["always_update"]
        self.assertGreater(practical["pairwise_ordering"], update["pairwise_ordering"])
        self.assertLess(practical["mean_normalized_regret"], update["mean_normalized_regret"])

    def test_guardrail_block_is_preserved(self) -> None:
        audit = self.result["guardrail_audit"]
        self.assertGreaterEqual(audit["blocked_decisions"], 1)
        banking = next(row for row in audit["decisions"] if row["panel_id"] == "benign_utility")
        self.assertEqual(banking["decision"], "block")

    def test_reproduction_is_byte_exact(self) -> None:
        expected = (ROOT / "results" / "summary.json").read_bytes()
        expected_manifest = (ROOT / "MANIFEST.sha256.json").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            original_out, original_manifest = self.module.OUT, self.module.MANIFEST
            try:
                self.module.OUT = temporary / "summary.json"
                self.module.MANIFEST = temporary / "manifest.json"
                self.module.main()
                self.assertEqual(self.module.OUT.read_bytes(), expected)
                self.assertEqual(self.module.MANIFEST.read_bytes(), expected_manifest)
            finally:
                self.module.OUT, self.module.MANIFEST = original_out, original_manifest


if __name__ == "__main__":
    unittest.main()
