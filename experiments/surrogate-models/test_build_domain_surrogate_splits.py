#!/usr/bin/env python3
"""Checks for the domain-centered replay split freeze."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_domain_surrogate_splits", HERE / "build_domain_surrogate_splits.py"
)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class DomainSurrogateSplitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.freeze = BUILDER.build()
        cls.suites = {row["suite_id"]: row for row in cls.freeze["suites"]}

    def test_expected_grouping(self) -> None:
        expected = {
            "controlled_leave_one_study_out": (69, 5),
            "coding_leave_one_decision_out": (104, 14),
            "materials_leave_one_study_out": (3010, 17),
            "finance_leave_one_study_out": (538, 16),
            "leave_one_domain_out": (3713, 5),
        }
        self.assertEqual(
            {key: (row["records"], row["groups"]) for key, row in self.suites.items()},
            expected,
        )

    def test_every_fold_is_complete_and_nonempty(self) -> None:
        for suite in self.freeze["suites"]:
            self.assertEqual(len(suite["folds"]), suite["groups"])
            for fold in suite["folds"]:
                self.assertGreater(fold["train_records"], 0)
                self.assertGreater(fold["test_records"], 0)
                self.assertEqual(fold["train_records"] + fold["test_records"], suite["records"])

    def test_checked_in_freeze_is_current(self) -> None:
        self.assertEqual(
            json.loads((HERE / "DOMAIN_SURROGATE_SPLITS.json").read_text()),
            self.freeze,
        )


if __name__ == "__main__":
    unittest.main()
