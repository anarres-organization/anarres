#!/usr/bin/env python3
"""Checks for the localized-regression evidence audit."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_regression_evidence_audit", HERE / "build_regression_evidence_audit.py"
)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class RegressionEvidenceAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = BUILDER.build_audit()

    def test_endpoint_classes_remain_separate(self) -> None:
        rows = {row["source_id"]: row for row in self.audit["sources"]}
        self.assertEqual(
            rows["finance_candidate_regressions"]["endpoint_class"],
            "candidate_relative_underperformance",
        )
        self.assertEqual(
            rows["legal_lab_task_regressions"]["endpoint_class"],
            "localized_absolute_regression",
        )

    def test_failed_prospective_results_do_not_advance(self) -> None:
        prospective = [
            row for row in self.audit["sources"] if row["chronology"].startswith("prospectively")
        ]
        self.assertEqual(len(prospective), 2)
        self.assertTrue(
            all(row["shared_model_eligibility"] == "negative_control_only" for row in prospective)
        )
        self.assertEqual(self.audit["summary"]["localized_prospective_successes"], 0)

    def test_nested_rows_do_not_justify_a_shared_model(self) -> None:
        self.assertFalse(self.audit["decision"]["fit_shared_localized_model"])

    def test_sources_are_content_addressed(self) -> None:
        for row in self.audit["sources"]:
            for item in row["artifacts"]:
                path = BUILDER.ROOT / item["path"]
                self.assertEqual(BUILDER.artifact(path), item)

    def test_checked_in_output_is_current(self) -> None:
        self.assertEqual((HERE / "REGRESSION_EVIDENCE_AUDIT.json").read_text(), BUILDER.render())


if __name__ == "__main__":
    unittest.main()
