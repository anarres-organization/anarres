#!/usr/bin/env python3
"""Tests for the target-conditional diagnostic."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class TargetConditionalDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "analyze_target_conditional_diagnostic.py")],
            check=True,
        )
        cls.result = json.loads(
            (ROOT / "results" / "target_conditional_diagnostic.json").read_text()
        )

    def test_support_is_unchanged(self) -> None:
        self.assertEqual(self.result["support"], {"sources": 16, "panels": 149, "arms": 538})

    def test_diagnostic_is_not_promoted(self) -> None:
        self.assertEqual(self.result["status"], "RETROSPECTIVE_DIAGNOSTIC__NOT_PROMOTED")
        evaluations = self.result["evaluations"]
        self.assertLessEqual(
            evaluations["derived_rule"]["pairwise_ordering"],
            evaluations["v2_rule"]["pairwise_ordering"],
        )
        self.assertLessEqual(
            evaluations["derived_ridge"]["pairwise_ordering"],
            evaluations["v2_ridge"]["pairwise_ordering"],
        )
        self.assertGreaterEqual(
            evaluations["derived_ridge"]["normalized_rmse"],
            evaluations["v2_ridge"]["normalized_rmse"],
        )


if __name__ == "__main__":
    unittest.main()
