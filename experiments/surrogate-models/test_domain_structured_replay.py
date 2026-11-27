#!/usr/bin/env python3
"""Checks for the domain-centered structured replay."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "run_domain_structured_replay", HERE / "run_domain_structured_replay.py"
)
assert SPEC and SPEC.loader
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class DomainStructuredReplayTest(unittest.TestCase):
    def test_model_views_are_current_and_identity_free(self) -> None:
        inputs = [
            json.loads(line)
            for line in (HERE / "DOMAIN_MODEL_INPUTS.jsonl").read_text().splitlines()
        ]
        self.assertTrue(inputs)
        for row in inputs:
            rendered = json.dumps(row["features"], sort_keys=True)
            self.assertNotIn("candidate_id", rendered)
            self.assertNotIn("panel_id", rendered)

    def test_released_result_covers_primary_suites(self) -> None:
        result = json.loads((HERE / "DOMAIN_STRUCTURED_RESULTS.json").read_text())
        self.assertEqual(set(result["suites"]), RUNNER.BASE.PRIMARY_SUITES)
        self.assertFalse(result["advancement_gate"]["passed"])

    def test_prediction_receipt_matches_predictions(self) -> None:
        result = json.loads((HERE / "DOMAIN_STRUCTURED_RESULTS.json").read_text())
        self.assertEqual(
            result["prediction_receipt"]["sha256"],
            RUNNER.BASE.sha256(HERE / "DOMAIN_STRUCTURED_PREDICTIONS.jsonl"),
        )


if __name__ == "__main__":
    unittest.main()
