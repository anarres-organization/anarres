"""Integrity checks for the frozen ProFinAgent component test."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class ProFinAgentHoldoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.score = json.loads((ROOT / "SCORE.json").read_text())
        specification = importlib.util.spec_from_file_location(
            "profinagent_score", ROOT / "score_holdout.py"
        )
        cls.module = importlib.util.module_from_spec(specification)
        assert specification.loader is not None
        specification.loader.exec_module(cls.module)

    def test_freeze_manifest(self) -> None:
        manifest = json.loads((ROOT / "FREEZE_MANIFEST.sha256.json").read_text())
        for name, expected in manifest.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)

    def test_component_results(self) -> None:
        self.assertEqual(self.score["prediction_families_correct"], 3)
        self.assertEqual(self.score["prediction_families_total"], 5)
        self.assertEqual(self.score["atomic_directional_checks"], {"correct": 19, "total": 19})
        self.assertEqual(
            self.score["accuracy_component_checks"]["full_over_dag_only"],
            {"correct": 9, "total": 9},
        )
        self.assertEqual(
            self.score["accuracy_component_checks"]["full_over_cbm_only"],
            {"correct": 9, "total": 9},
        )

    def test_failed_predictions_are_visible(self) -> None:
        outcomes = {row["id"]: row["correct"] for row in self.score["predictions"]}
        self.assertFalse(outcomes["tools_largest_on_procedural_computation"])
        self.assertFalse(outcomes["full_system_not_uniformly_best"])

    def test_reproduction_is_byte_exact(self) -> None:
        expected_score = (ROOT / "SCORE.json").read_bytes()
        expected_manifest = (ROOT / "MANIFEST.sha256.json").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            original_score, original_manifest = self.module.SCORE, self.module.MANIFEST
            try:
                self.module.SCORE = temporary / "score.json"
                self.module.MANIFEST = temporary / "manifest.json"
                self.module.main()
                self.assertEqual(self.module.SCORE.read_bytes(), expected_score)
                self.assertEqual(self.module.MANIFEST.read_bytes(), expected_manifest)
            finally:
                self.module.SCORE, self.module.MANIFEST = original_score, original_manifest


if __name__ == "__main__":
    unittest.main()
