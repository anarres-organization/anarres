#!/usr/bin/env python3
"""Checks for the released cross-domain intervention inventory."""

from __future__ import annotations

import importlib.util
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_corpus_inventory", HERE / "build_corpus_inventory.py"
)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class CorpusInventoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = BUILDER.build_inventory()

    def test_released_counts(self) -> None:
        summary = self.inventory["summary"]
        self.assertEqual(summary["sources"], 24)
        self.assertEqual(summary["records"], 3641)
        self.assertEqual(
            summary["records_by_domain"],
            {
                "finance": 538,
                "legal": 9,
                "materials_science": 3010,
                "mathematics": 32,
                "robotics": 52,
            },
        )
        self.assertEqual(
            summary["records_by_evidence_level"],
            {
                "published_candidate_arm_aggregate": 3540,
                "seed_level_intervention": 101,
            },
        )

    def test_every_panel_has_multiple_candidates(self) -> None:
        candidates: dict[tuple[str, str], set[str]] = {}
        for row in self.inventory["records"]:
            key = (row["source_id"], row["panel_id"])
            candidates.setdefault(key, set()).add(row["candidate_id"])
        singletons = sorted(key for key, values in candidates.items() if len(values) < 2)
        self.assertEqual(singletons, [])

    def test_seed_level_runs_are_not_inflated_by_checkpoints(self) -> None:
        counts = Counter(
            row["source_id"]
            for row in self.inventory["records"]
            if row["evidence_level"] == "seed_level_intervention"
        )
        self.assertEqual(
            counts,
            {
                "legal_syllogym_prospective": 9,
                "materials_mlip_phonon_prospective": 8,
                "mathematics_environment_utility": 32,
                "robotics_can_v141_prospective": 25,
                "robotics_pusht_prospective": 9,
                "robotics_square_regression_prospective": 18,
            },
        )

    def test_missing_cost_is_explicit_and_never_zero_filled(self) -> None:
        for row in self.inventory["records"]:
            self.assertIn("status", row["cost"])
            for key, value in row["cost"].items():
                if key != "status" and value is not None:
                    self.assertGreaterEqual(value, 0)

    def test_sources_are_content_addressed(self) -> None:
        for source in self.inventory["sources"]:
            self.assertTrue(source["artifacts"])
            for item in source["artifacts"]:
                path = BUILDER.ROOT / item["path"]
                self.assertEqual(BUILDER.digest(path), item["sha256"])
                self.assertEqual(path.stat().st_size, item["bytes"])

    def test_checked_in_inventory_is_current(self) -> None:
        manifest_rendered, records_rendered = BUILDER.render_inventory(
            self.inventory, "CORPUS_RECORDS.jsonl"
        )
        self.assertEqual((HERE / "CORPUS_INVENTORY.json").read_text(), manifest_rendered)
        self.assertEqual((HERE / "CORPUS_RECORDS.jsonl").read_text(), records_rendered)


if __name__ == "__main__":
    unittest.main()
