#!/usr/bin/env python3
"""Checks for the domain-centered surrogate inventory."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_domain_surrogate_inventory", HERE / "build_domain_surrogate_inventory.py"
)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class DomainSurrogateInventoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory, cls.records = BUILDER.build_inventory()

    def test_priority_domains_replace_mathematics_as_headline_evidence(self) -> None:
        counts = self.inventory["tracks"]["utility"]["records_by_domain"]
        self.assertNotIn("mathematics", counts)
        self.assertEqual(counts["agentic_coding"], 104)
        self.assertEqual(set(counts), BUILDER.PRIORITY_DOMAINS | {"agentic_coding"})

    def test_coding_endpoints_remain_nested_under_fourteen_decisions(self) -> None:
        coding = [row for row in self.records if row["domain"] == "agentic_coding"]
        self.assertEqual(len({row["study_id"] for row in coding}), 14)
        self.assertEqual(len({row["panel_id"] for row in coding}), 27)

    def test_regression_rows_do_not_inflate_intervention_count(self) -> None:
        regressions = self.inventory["regression_sources"]
        self.assertEqual(
            {row["domain"] for row in regressions},
            {"agentic_coding", "legal", "materials_science", "robotics"},
        )
        self.assertEqual(
            next(row for row in regressions if row["domain"] == "legal")["interventions"],
            1,
        )

    def test_sources_are_content_addressed(self) -> None:
        rows = [*self.inventory["coding_sources"], *self.inventory["regression_sources"]]
        for row in rows:
            for item in row["artifacts"]:
                path = BUILDER.ROOT / item["path"]
                self.assertEqual(BUILDER.sha256(path), item["sha256"])

    def test_checked_in_outputs_are_current(self) -> None:
        inventory, records = BUILDER.render()
        self.assertEqual((HERE / "DOMAIN_SURROGATE_INVENTORY.json").read_text(), inventory)
        self.assertEqual((HERE / "DOMAIN_SURROGATE_RECORDS.jsonl").read_text(), records)


if __name__ == "__main__":
    unittest.main()
