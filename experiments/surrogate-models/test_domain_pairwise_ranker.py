#!/usr/bin/env python3
"""Checks for the domain-aware pairwise-ranker replay."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "run_domain_pairwise_ranker", HERE / "run_domain_pairwise_ranker.py"
)
assert SPEC and SPEC.loader
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


class DomainPairwiseRankerTest(unittest.TestCase):
    def test_contract_and_receipt_precede_scoring(self) -> None:
        contract = json.loads(RUNNER.CONTRACT.read_text())
        receipt = json.loads(RUNNER.FITS.read_text())
        self.assertEqual(
            contract["status"], "frozen before fitting or scoring the pairwise rankers"
        )
        self.assertEqual(receipt["contract_sha256"], RUNNER.sha256(RUNNER.CONTRACT))
        self.assertEqual(receipt["predictions"]["sha256"], RUNNER.sha256(RUNNER.PREDICTIONS))

    def test_released_result_covers_every_primary_suite(self) -> None:
        result = json.loads(RUNNER.RESULTS.read_text())
        self.assertEqual(set(result["suites"]), RUNNER.PRIMARY_SUITES)
        self.assertFalse(result["advancement_gate"]["passed"])
        self.assertFalse(result["advancement_gate"]["cost_criterion_scored"])
        self.assertFalse(result["advancement_gate"]["abstention_criterion_scored"])

    def test_identity_keys_are_not_model_features(self) -> None:
        for row in RUNNER.read_jsonl(RUNNER.INPUTS):
            rendered = json.dumps(row["feature_views"], sort_keys=True)
            self.assertNotIn(row["candidate_key"], rendered)
            self.assertNotIn(row["partition"]["panel_key"], rendered)
            self.assertNotIn(row["partition"]["study_key"], rendered)

    def test_retrieval_history_matches_each_fitting_partition(self) -> None:
        splits = json.loads(RUNNER.SPLITS.read_text())
        for suite in splits["suites"]:
            for fold in suite["folds"]:
                self.assertEqual(
                    fold["retrieval_history_candidate_keys_sha256"],
                    fold["train_candidate_keys_sha256"],
                )
                for inner in fold["inner_folds"]:
                    self.assertEqual(
                        inner["retrieval_history_candidate_keys_sha256"],
                        inner["train_candidate_keys_sha256"],
                    )


if __name__ == "__main__":
    unittest.main()
