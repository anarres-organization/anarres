#!/usr/bin/env python3
"""Checks for the transparent Grug mixture-surrogate baselines."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "run_grug_swarm_baselines", HERE / "run_grug_swarm_baselines.py"
)
assert SPEC and SPEC.loader
BASELINES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASELINES)


class GrugSwarmBaselineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.results = json.loads((HERE / "GRUG_SWARM_BASELINE_RESULTS.json").read_text())

    def test_results_reproduce(self) -> None:
        self.assertTrue(BASELINES.numerically_equal(self.results, BASELINES.build_results()))

    def test_reproduction_tolerance_does_not_hide_material_changes(self) -> None:
        self.assertTrue(BASELINES.numerically_equal(0.5, 0.5005))
        self.assertFalse(BASELINES.numerically_equal(0.5, 0.502))

    def test_honest_splits_are_reported(self) -> None:
        splits = self.results["split_contract"]
        self.assertIn("lineage_five_fold", splits)
        self.assertIn("leave_one_design_family_out", splits)
        self.assertIn("absent from training", splits["selected_pair"])

    def test_complexity_ladder_includes_nonparametric_route(self) -> None:
        models = self.results["models"]
        self.assertEqual(models["linear_ridge"]["features"], "all 400 two-phase cell weights")
        self.assertIn("hellinger_rbf_kernel", models)
        self.assertIn("content_hellinger_rbf_kernel", models)

    def test_selected_pair_is_not_presented_as_independent(self) -> None:
        self.assertIn("not independent", self.results["interpretation_boundary"])
        comparison = self.results["published_selected_pair"]
        self.assertEqual(
            set(comparison["content_hellinger_rbf_kernel"]),
            {"capability_log_probability", "held_out_loss_or_bpb"},
        )

    def test_support_gate_identifies_higher_error_extrapolations(self) -> None:
        gate = self.results["support_gate"]
        self.assertEqual(gate["model"], "content_hellinger_rbf_kernel")
        for audit in gate["results"].values():
            self.assertLess(
                audit["accepted_mean_absolute_standardized_error"],
                audit["rejected_mean_absolute_standardized_error"],
            )
        self.assertLess(
            gate["results"]["leave_one_design_family_out"]["accepted_lineage_fraction"],
            gate["results"]["lineage_five_fold"]["accepted_lineage_fraction"],
        )


if __name__ == "__main__":
    unittest.main()
