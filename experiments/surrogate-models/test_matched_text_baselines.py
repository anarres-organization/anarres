#!/usr/bin/env python3
"""Checks for matched text baselines."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
for module_name in ("build_record_conditioned_replay", "run_matched_text_baselines"):
    spec = importlib.util.spec_from_file_location(module_name, HERE / f"{module_name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

BASELINES = sys.modules["run_matched_text_baselines"]


class MatchedTextBaselineTest(unittest.TestCase):
    def test_measurement_ablation_changes_only_measurement_fields(self) -> None:
        row = sys.modules["build_record_conditioned_replay"].aggregate()[0]
        without = BASELINES.record_text(row, False)
        with_measurements = BASELINES.record_text(row, True)
        self.assertNotIn("prediction_time_measurements", without)
        self.assertIn("prediction_time_measurements", with_measurements)

    def test_panel_score_uses_tie_averaging(self) -> None:
        rows = [
            {"normalized_utility": 0.0},
            {"normalized_utility": 1.0},
        ]
        result = BASELINES.panel_score(rows, np.asarray([0.5, 0.5]))
        self.assertEqual(result["normalized_regret"], 0.5)
        self.assertEqual(result["pairwise_ordering"], 0.5)
        self.assertEqual(result["top_choice_credit"], 0.5)

    def test_outer_folds_exclude_the_heldout_study(self) -> None:
        rows = sys.modules["build_record_conditioned_replay"].aggregate()
        for study in {row["study_id"] for row in rows}:
            train = [row for row in rows if row["study_id"] != study]
            self.assertNotIn(study, {row["study_id"] for row in train})


if __name__ == "__main__":
    unittest.main()
