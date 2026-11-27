#!/usr/bin/env python3
"""Checks for the released-baseline audit."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_baseline_audit", HERE / "build_baseline_audit.py"
)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class BaselineAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = BUILDER.build_audit()

    def test_support_matches_released_results(self) -> None:
        studies = self.audit["studies"]
        self.assertEqual(
            studies["materials"]["support"], {"sources": 16, "panels": 804, "arms": 3002}
        )
        self.assertEqual(studies["finance"]["support"], {"sources": 16, "panels": 149, "arms": 538})

    def test_native_rules_are_the_current_regret_baselines(self) -> None:
        for domain in ("materials", "finance"):
            study = self.audit["studies"][domain]
            self.assertEqual(study["strongest_released_method_by_regret"], "released_native_rule")
            self.assertGreater(study["ridge_minus_native_rule_regret"], 0.0)

    def test_sources_are_content_addressed(self) -> None:
        for source in self.audit["sources"].values():
            self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")

    def test_checked_in_audit_is_current(self) -> None:
        checked_in = json.loads((HERE / "BASELINE_AUDIT.json").read_text())
        self.assertEqual(checked_in, self.audit)


if __name__ == "__main__":
    unittest.main()
