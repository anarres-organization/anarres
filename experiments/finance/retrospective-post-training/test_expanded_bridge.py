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
SCRIPT = ROOT / "scripts" / "reproduce_expanded_bridge.py"
SUMMARY = ROOT / "results" / "expanded_summary.json"
MANIFEST = ROOT / "results" / "EXPANDED_MANIFEST.sha256.json"


class ExpandedBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, str(SCRIPT)], check=True, capture_output=True)
        cls.summary = json.loads(SUMMARY.read_text())

    def test_support(self) -> None:
        self.assertEqual(self.summary["support"], {"sources": 16, "panels": 149, "arms": 538})

    def test_required_holdouts_and_controls(self) -> None:
        self.assertEqual(
            set(self.summary["evaluations"]),
            {"leave_one_source_out", "leave_one_model_out", "leave_one_target_out"},
        )
        required = {
            "ridge",
            "compact_ridge",
            "practical_rule",
            "more_data",
            "uninformed",
            "random_fingerprint",
        }
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
        self.assertLess(
            result["compact_ridge"]["source_macro"]["normalized_rmse"],
            result["more_data"]["source_macro"]["normalized_rmse"],
        )
        self.assertGreater(
            result["practical_rule"]["pairwise_ordering"],
            result["random_fingerprint"]["pairwise_ordering"],
        )

    def test_study_weighting_and_rank_sensitivity(self) -> None:
        result = self.summary["evaluations"]["leave_one_source_out"]
        self.assertLess(
            result["practical_rule"]["source_macro"]["mean_normalized_regret"],
            result["more_data"]["source_macro"]["mean_normalized_regret"],
        )
        ranked = self.summary["rank_utility_sensitivity"]
        self.assertLess(
            ranked["practical_rule"]["source_macro"]["mean_normalized_regret"],
            ranked["more_data"]["source_macro"]["mean_normalized_regret"],
        )
        comparison = self.summary["paired_source_comparison"]
        self.assertGreater(comparison["study_wins"], comparison["study_losses"])
        multi_panel = self.summary["multi_panel_source_sensitivity"]
        self.assertEqual(multi_panel["support"]["sources"], 14)
        self.assertLess(
            multi_panel["evaluations"]["practical_rule"]["source_macro"]["mean_normalized_regret"],
            multi_panel["evaluations"]["more_data"]["source_macro"]["mean_normalized_regret"],
        )

    def test_time_and_influence_sensitivities(self) -> None:
        temporal = self.summary["publication_cutoff_sensitivity"]
        self.assertEqual(temporal["cutoff_year"], 2026)
        self.assertEqual(temporal["train_support"]["sources"], 7)
        self.assertEqual(temporal["test_support"]["sources"], 9)
        self.assertLess(
            temporal["evaluations"]["ridge"]["source_macro"]["mean_normalized_regret"],
            temporal["evaluations"]["more_data"]["source_macro"]["mean_normalized_regret"],
        )
        influence = self.summary["source_exclusion_sensitivity"]
        self.assertTrue(influence["all_source_exclusions_preserve_direction"])
        self.assertGreater(influence["minimum_gap"], 0.0)
        feature_ablation = self.summary["practical_feature_ablation"]
        self.assertGreater(feature_ablation["ordering_range"][0], 0.70)
        self.assertLess(feature_ablation["regret_range"][1], 0.25)
        penalties = self.summary["ridge_penalty_sensitivity"]
        self.assertEqual(set(penalties), {"0.5", "1.0", "2.0", "4.0", "8.0", "16.0"})
        for result in penalties.values():
            self.assertGreater(result["ridge"]["pairwise_ordering"], 0.70)

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
                "scripts/reproduce_expanded_bridge.py",
                "results/expanded_summary.json",
            },
        )
        for relative_path, expected in manifest.items():
            observed = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
            self.assertEqual(observed, expected)


if __name__ == "__main__":
    unittest.main()
