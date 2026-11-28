#!/usr/bin/env python3
"""Checks for the learned history-support gate."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "run_history_support_gate", HERE / "run_history_support_gate.py"
)
assert SPEC and SPEC.loader
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


class HistorySupportGateTest(unittest.TestCase):
    def test_receipt_matches_contract_and_predictions(self) -> None:
        receipt = json.loads(RUNNER.FITS.read_text())
        self.assertEqual(receipt["contract_sha256"], RUNNER.sha256(RUNNER.CONTRACT))
        self.assertEqual(receipt["predictions"]["sha256"], RUNNER.sha256(RUNNER.PREDICTIONS))
        self.assertEqual(receipt["predictions"]["rows"], 89)

    def test_every_study_is_held_out_once(self) -> None:
        panels = RUNNER.load_panels()
        expected = {panel.study for panel in panels}
        receipt = json.loads(RUNNER.FITS.read_text())
        observed = {fit["heldout_study"] for fit in receipt["fits"]}
        self.assertEqual(observed, expected)
        self.assertTrue(all(fit["train_studies"] == len(expected) - 1 for fit in receipt["fits"]))

    def test_result_retains_development_boundary(self) -> None:
        result = json.loads(RUNNER.RESULTS.read_text())
        self.assertFalse(result["advancement_gate"]["passed"])
        self.assertFalse(result["advancement_gate"]["independent_prospective_test"])
        self.assertFalse(result["advancement_gate"]["total_research_cost_scored"])
        self.assertGreater(result["history_support_calibration"]["roc_auc"], 0.5)

    def test_gate_costs_only_selected_history_requests(self) -> None:
        predictions = RUNNER.read_jsonl(RUNNER.PREDICTIONS)
        history_requests = sum(row["selected_condition"] == RUNNER.HISTORY for row in predictions)
        result = json.loads(RUNNER.RESULTS.read_text())
        self.assertEqual(
            result["route_inference"]["learned_history_gate"]["requests"],
            len(predictions) + history_requests,
        )


if __name__ == "__main__":
    unittest.main()
