#!/usr/bin/env python3
"""Checks for the grouped structured-surrogate replay."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "run_structured_replay", HERE / "run_structured_replay.py"
)
assert SPEC and SPEC.loader
REPLAY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REPLAY
SPEC.loader.exec_module(REPLAY)


class StructuredReplayTest(unittest.TestCase):
    def test_training_outcome_loader_respects_allowlist(self) -> None:
        records = REPLAY.load_records()
        allowed = {record.join_key for record in records[:7]}
        outcomes = REPLAY.load_outcomes(allowed)
        self.assertEqual(set(outcomes), allowed)

    def test_checked_in_predictions_cover_primary_suites(self) -> None:
        predictions = REPLAY.read_jsonl(REPLAY.PREDICTIONS)
        suites = {row["suite_id"] for row in predictions}
        self.assertEqual(suites, REPLAY.PRIMARY_SUITES)
        self.assertTrue(all(row["join_keys"] for row in predictions))
        self.assertTrue(
            all(len(row["join_keys"]) == row["candidate_seed_records"] for row in predictions)
        )

    def test_fit_receipt_binds_predictions(self) -> None:
        receipt = json.loads(REPLAY.FITS.read_text())
        self.assertEqual(receipt["sha256"], REPLAY.sha256(REPLAY.PREDICTIONS))
        self.assertEqual(receipt["status"], "predictions_written_before_heldout_scoring")

    def test_scoring_is_deterministic_and_gate_is_explicit(self) -> None:
        expected = REPLAY.RESULTS.read_bytes()
        result = REPLAY.score()
        self.assertEqual(REPLAY.RESULTS.read_bytes(), expected)
        self.assertFalse(result["advancement_gate"]["regret_and_regression_pass"])
        self.assertFalse(result["advancement_gate"]["cost_criterion_scored"])
        self.assertFalse(result["advancement_gate"]["abstention_criterion_scored"])
        self.assertFalse(result["advancement_gate"]["passed"])
        self.assertFalse(result["advancement_gate"]["prospective_followup_authorized"])
        self.assertEqual(
            result["advancement_gate"]["decision"],
            "do not advance this structured predictor to a prospective test",
        )


if __name__ == "__main__":
    unittest.main()
