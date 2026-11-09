#!/usr/bin/env python3
"""Integrity checks for the expanded grouped finance bridge."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "analyze_expanded_bridge.py"
SUMMARY = ROOT / "results" / "expanded_summary.json"
MANIFEST = ROOT / "results" / "EXPANDED_MANIFEST.sha256.json"


class ExpandedBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, str(SCRIPT)], check=True, capture_output=True)
        cls.summary = json.loads(SUMMARY.read_text())

    def test_support(self) -> None:
        self.assertEqual(self.summary["support"], {"sources": 10, "panels": 90, "arms": 377})

    def test_required_holdouts_and_controls(self) -> None:
        self.assertEqual(
            set(self.summary["evaluations"]),
            {"leave_one_source_out", "leave_one_model_out", "leave_one_target_out"},
        )
        required = {"ridge", "practical_rule", "more_data", "uninformed", "random_fingerprint"}
        for result in self.summary["evaluations"].values():
            self.assertEqual(set(result), required)

    def test_source_holdout_claims(self) -> None:
        result = self.summary["evaluations"]["leave_one_source_out"]
        self.assertLess(
            result["practical_rule"]["mean_normalized_regret"],
            result["more_data"]["mean_normalized_regret"],
        )
        self.assertLess(
            result["ridge"]["normalized_rmse"],
            result["uninformed"]["normalized_rmse"],
        )
        self.assertGreater(
            result["practical_rule"]["pairwise_ordering"],
            result["random_fingerprint"]["pairwise_ordering"],
        )

    def test_shuffled_pairing_is_not_claim_evidence(self) -> None:
        shuffled = self.summary["shuffled_pairing_control"]
        observed = self.summary["evaluations"]["leave_one_source_out"]["practical_rule"]
        self.assertEqual(shuffled["repeats"], 200)
        self.assertLess(observed["mean_normalized_regret"], shuffled["p05_regret"])

    def test_expanded_manifest(self) -> None:
        manifest = json.loads(MANIFEST.read_text())
        self.assertEqual(
            set(manifest),
            {
                "FEATURE_MAPPING.md",
                "SOURCES.json",
                "data/panels.json",
                "data/recovered_panels.json",
                "scripts/build_recovered_panels.py",
                "scripts/analyze_expanded_bridge.py",
                "results/expanded_summary.json",
            },
        )
        for relative_path, expected in manifest.items():
            observed = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
            self.assertEqual(observed, expected)


if __name__ == "__main__":
    unittest.main()
