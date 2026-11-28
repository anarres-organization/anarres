#!/usr/bin/env python3
"""Checks for the normalized Snowball Exp5 intervention record."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class SnowballExp5InterventionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.record = json.loads((HERE / "SNOWBALL_EXP5_INTERVENTION.json").read_text())

    def test_environment_weights_form_one_policy(self) -> None:
        sources = self.record["environment"]["sources"]
        self.assertEqual(len(sources), 11)
        self.assertAlmostEqual(sum(row["weight"] for row in sources), 1.0)
        self.assertEqual(
            self.record["environment"]["route_quotas"], {"agentic": 13, "nonagentic": 51}
        )

    def test_native_target_summary_is_recomputed(self) -> None:
        rows = self.record["native_target_changes"]
        changes = [row["rl"] - row["sft"] for row in rows]
        summary = self.record["summary"]
        self.assertEqual(
            len(rows), self.record["evaluation_contract"]["common_informative_targets"]
        )
        self.assertAlmostEqual(summary["mean_target_change"], sum(changes) / len(changes), places=4)
        self.assertEqual(summary["improved_targets"], sum(change > 0 for change in changes))
        self.assertEqual(summary["regressed_targets"], sum(change < 0 for change in changes))
        self.assertEqual(summary["tied_targets"], sum(change == 0 for change in changes))

    def test_outcomes_do_not_become_prediction_inputs(self) -> None:
        readiness = self.record["prediction_readiness"]
        self.assertFalse(readiness["starting_policy_environment_measurements"])
        self.assertFalse(readiness["matched_candidate_panel"])
        self.assertFalse(readiness["eligible_for_surrogate_fitting"])
        self.assertIn("does not predict", self.record["boundary"])


if __name__ == "__main__":
    unittest.main()
