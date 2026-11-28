#!/usr/bin/env python3
"""Checks for the Grug target-level relative-harm audit."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SPEC = importlib.util.spec_from_file_location(
    "audit_grug_relative_harm", HERE / "audit_grug_relative_harm.py"
)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class GrugRelativeHarmTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = json.loads((HERE / "GRUG_SWARM_RELATIVE_HARM_RESULTS.json").read_text())

    def test_result_reproduces(self) -> None:
        self.assertTrue(AUDIT.baselines.numerically_equal(self.result, AUDIT.build()))

    def test_reference_and_candidates_are_grouped(self) -> None:
        contract = self.result["contract"]
        self.assertEqual(contract["reference_runs"], 3)
        self.assertEqual(contract["candidate_lineages"], 914)
        self.assertIn("complete held-out lineage", contract["fit_exclusion"])

    def test_content_model_beats_mean_control_on_held_out_families(self) -> None:
        results = self.result["results"]["leave_one_design_family_out"]
        content = results["content_hellinger_rbf_kernel"]["all_targets"]
        control = results["training_mean"]["all_targets"]
        self.assertGreater(content["roc_auc"], control["roc_auc"])
        self.assertGreater(content["average_precision"], control["average_precision"])
        self.assertGreater(content["top_risk_recall_lift"], 1.0)

    def test_result_does_not_claim_calibrated_risk(self) -> None:
        self.assertIn("not calibrated", self.result["status"])
        self.assertIn("no probability calibration", self.result["interpretation_boundary"])


if __name__ == "__main__":
    unittest.main()
