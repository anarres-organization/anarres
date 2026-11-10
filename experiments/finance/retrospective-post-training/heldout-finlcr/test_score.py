#!/usr/bin/env python3
"""Regression tests for the frozen FinLCR component score."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_score_module():
    specification = importlib.util.spec_from_file_location(
        "finlcr_score", HERE / "score_holdout.py"
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load FinLCR scorer")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class FinLcrScoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_score_module()
        cls.score = cls.module.score()

    def test_freeze_manifest_still_matches(self) -> None:
        manifest = json.loads((HERE / "FREEZE_MANIFEST.sha256.json").read_text())
        for relative, expected in manifest.items():
            self.assertEqual(self.module.digest(HERE / relative), expected)

    def test_all_reported_matched_predictions_are_correct(self) -> None:
        self.assertEqual(self.score["component_correct"], 3)
        self.assertEqual(self.score["component_scored"], 3)
        self.assertEqual(self.score["regression_correct"], 1)
        self.assertEqual(self.score["regression_scored"], 1)
        self.assertEqual(len(self.score["unscored_predictions"]), 1)

    def test_interaction_is_preserved(self) -> None:
        interaction = self.score["interaction_diagnostic"]
        self.assertLess(interaction["s2l_only_minus_naive_gspo"], 0)
        self.assertLess(interaction["das_only_minus_naive_gspo"], 0)
        self.assertGreater(interaction["combined_minus_naive_gspo"], 0)


if __name__ == "__main__":
    unittest.main()
