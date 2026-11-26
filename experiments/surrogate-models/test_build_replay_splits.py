#!/usr/bin/env python3
"""Checks for the grouped surrogate replay freeze."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_replay_splits", HERE / "build_replay_splits.py"
)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class ReplaySplitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.freeze = BUILDER.build_splits()
        cls.suites = {suite["suite_id"]: suite for suite in cls.freeze["suites"]}

    def test_suite_counts(self) -> None:
        expected = {
            "seed_level_leave_one_study_out": (101, 6),
            "materials_leave_one_publication_out": (3002, 16),
            "finance_leave_one_study_out": (538, 16),
            "leave_one_domain_out": (3641, 5),
            "mathematics_leave_one_scale_out": (32, 4),
        }
        self.assertEqual(
            {key: (suite["records"], suite["groups"]) for key, suite in self.suites.items()},
            expected,
        )

    def test_every_fold_is_nonempty_and_complete(self) -> None:
        for suite in self.freeze["suites"]:
            self.assertEqual(len(suite["folds"]), suite["groups"])
            for fold in suite["folds"]:
                self.assertGreater(fold["train_records"], 0)
                self.assertGreater(fold["test_records"], 0)
                self.assertEqual(fold["train_records"] + fold["test_records"], suite["records"])

    def test_fold_digests_resolve_from_the_corpus(self) -> None:
        records = BUILDER.load_records()
        for suite in self.freeze["suites"]:
            selected = [row for row in records if BUILDER.matches(row, suite["filters"])]
            self.assertEqual(BUILDER.record_set_digest(selected), suite["record_ids_sha256"])
            for fold in suite["folds"]:
                selector = fold["test_selector"]
                test = [
                    row
                    for row in selected
                    if str(BUILDER.nested(row, selector["field"])) == selector["value"]
                ]
                test_ids = {row["record_id"] for row in test}
                train = [row for row in selected if row["record_id"] not in test_ids]
                self.assertEqual(BUILDER.record_set_digest(test), fold["test_record_ids_sha256"])
                self.assertEqual(BUILDER.record_set_digest(train), fold["train_record_ids_sha256"])

    def test_checked_in_freeze_is_current(self) -> None:
        checked_in = json.loads((HERE / "REPLAY_SPLITS.json").read_text())
        self.assertEqual(checked_in, self.freeze)


if __name__ == "__main__":
    unittest.main()
