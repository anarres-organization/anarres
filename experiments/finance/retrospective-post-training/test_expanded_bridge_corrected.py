#!/usr/bin/env python3
"""Tests for the corrected expanded finance bridge."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "analyze_expanded_bridge_corrected.py"


def load_corrected():
    spec = importlib.util.spec_from_file_location("finance_bridge_corrected", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CorrectedBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, str(SCRIPT)], check=True)
        cls.result = json.loads((ROOT / "results" / "expanded_summary_corrected.json").read_text())

    def test_support_is_preserved(self) -> None:
        self.assertEqual(self.result["support"], {"sources": 16, "panels": 149, "arms": 538})

    def test_no_training_controls_have_zero_alignment(self) -> None:
        module = load_corrected()
        bridge = module.load_v2()
        rows = module.corrected_rows(bridge)
        controls = [
            row
            for row in rows
            if row["source"] in {"oda_fin", "fino1", "data_centric_finance", "quanteval"}
            and row["arm"].startswith("base")
        ]
        self.assertTrue(controls)
        self.assertTrue(all(row["feature_values"]["target_alignment"] == 0 for row in controls))

    def test_main_direction_is_preserved(self) -> None:
        evaluations = self.result["evaluations"]["leave_one_source_out"]
        practical = evaluations["practical_rule"]["source_macro"]
        more_data = evaluations["more_data"]["source_macro"]
        self.assertGreater(practical["pairwise_ordering"], more_data["pairwise_ordering"])
        self.assertLess(practical["mean_normalized_regret"], more_data["mean_normalized_regret"])


if __name__ == "__main__":
    unittest.main()
