#!/usr/bin/env python3
"""Checks for the frozen domain-aware surrogate contract."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACT = HERE / "DOMAIN_AWARE_SURROGATE_CONTRACT.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DomainAwareSurrogateContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text())

    def test_development_artifacts_are_content_addressed(self) -> None:
        expected = {
            "domain_record_conditioned_prediction_receipt_sha256": (
                "DOMAIN_RECORD_CONDITIONED_PREDICTION_RECEIPT.json"
            ),
            "domain_record_conditioned_results_sha256": ("DOMAIN_RECORD_CONDITIONED_RESULTS.json"),
            "domain_surrogate_inventory_sha256": "DOMAIN_SURROGATE_INVENTORY.json",
            "domain_surrogate_splits_sha256": "DOMAIN_SURROGATE_SPLITS.json",
        }
        for field, filename in expected.items():
            self.assertEqual(self.contract["development_evidence"][field], sha256(HERE / filename))

    def test_every_prediction_route_requires_measurements(self) -> None:
        routes = self.contract["frozen_comparator"]
        for route in routes.values():
            if route["action"].startswith("predict"):
                self.assertIn("with_measurements", route["condition"])

    def test_sparse_and_unseen_domains_abstain(self) -> None:
        routes = self.contract["frozen_comparator"]
        self.assertEqual(routes["legal"]["action"], "abstain")
        self.assertEqual(routes["unseen_domain"]["action"], "abstain")
        self.assertIsNone(routes["legal"]["condition"])
        self.assertIsNone(routes["unseen_domain"]["condition"])

    def test_regression_and_utility_tracks_remain_separate(self) -> None:
        candidate = self.contract["learned_candidate"]
        self.assertIn("localized regression", candidate["regression_track"])
        self.assertIn("within-panel ordering", candidate["utility_track"])


if __name__ == "__main__":
    unittest.main()
