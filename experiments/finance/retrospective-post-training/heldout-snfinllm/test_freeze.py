#!/usr/bin/env python3
"""Check the SNFinLLM holdout freeze and prediction artifact."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


class HoldoutFreezeTests(unittest.TestCase):
    def test_study_is_absent_from_fitted_sources(self) -> None:
        sources = json.loads((ROOT / "SOURCES.json").read_text())
        self.assertNotIn("snfinllm_2024", {source["id"] for source in sources["sources"]})

    def test_representation_hashes(self) -> None:
        freeze = json.loads((HERE / "FREEZE.json").read_text())["representation"]
        paths = {
            "feature_mapping_sha256": ROOT / "FEATURE_MAPPING.md",
            "analysis_script_sha256": ROOT / "scripts" / "analyze_expanded_bridge.py",
            "expanded_summary_sha256": ROOT / "results" / "expanded_summary.json",
            "source_registry_sha256": ROOT / "SOURCES.json",
        }
        for key, path in paths.items():
            self.assertEqual(freeze[key], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_predictions_reproduce(self) -> None:
        expected = (HERE / "PREDICTIONS.sha256").read_text().split()[0]
        observed = hashlib.sha256((HERE / "PREDICTIONS.json").read_bytes()).hexdigest()
        self.assertEqual(expected, observed)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "PREDICTIONS.json"
            hash_output = Path(directory) / "PREDICTIONS.sha256"
            subprocess.run(
                [
                    sys.executable,
                    str(HERE / "freeze_predictions.py"),
                    "--output",
                    str(output),
                    "--hash-output",
                    str(hash_output),
                ],
                check=True,
            )
            regenerated = json.loads(output.read_text())
            regenerated_hash = hash_output.read_text().split()[0]
            self.assertEqual(regenerated_hash, hashlib.sha256(output.read_bytes()).hexdigest())

        frozen = json.loads((HERE / "PREDICTIONS.json").read_text())
        self.assertEqual(regenerated["status"], frozen["status"])
        self.assertEqual(regenerated["representation_commit"], frozen["representation_commit"])
        self.assertEqual(regenerated["candidate_file_sha256"], frozen["candidate_file_sha256"])
        self.assertEqual(regenerated["ranking_tiers"], frozen["ranking_tiers"])
        self.assertEqual(regenerated["interpretation"], frozen["interpretation"])
        self.assertEqual(set(regenerated["predictions"]), set(frozen["predictions"]))
        for arm, prediction in frozen["predictions"].items():
            candidate = regenerated["predictions"][arm]
            self.assertEqual(candidate["feature_values"], prediction["feature_values"])
            self.assertEqual(candidate["practical_rule"], prediction["practical_rule"])
            self.assertEqual(candidate["more_data"], prediction["more_data"])
            self.assertAlmostEqual(candidate["full_ridge"], prediction["full_ridge"], places=14)
            self.assertAlmostEqual(
                candidate["compact_ridge"], prediction["compact_ridge"], places=14
            )


if __name__ == "__main__":
    unittest.main()
