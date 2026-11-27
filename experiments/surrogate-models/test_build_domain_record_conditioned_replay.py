#!/usr/bin/env python3
"""Checks for the domain record-conditioned prompt freeze."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_domain_record_conditioned_replay",
    HERE / "build_domain_record_conditioned_replay.py",
)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class DomainRecordConditionedReplayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prompts, cls.labels = BUILDER.render()
        cls.prompt_rows = [json.loads(line) for line in cls.prompts.splitlines()]
        cls.label_rows = [json.loads(line) for line in cls.labels.splitlines()]

    def test_target_outcomes_never_enter_prompts(self) -> None:
        prompt_keys = {row["prompt_id"] for row in self.prompt_rows}
        self.assertEqual(prompt_keys, {row["prompt_id"] for row in self.label_rows})
        for row in self.prompt_rows:
            payload = json.loads(row["user"])
            for candidate in payload["target_candidates"]:
                self.assertLessEqual(
                    set(candidate),
                    {"candidate_key", "description", "prediction_time_measurements"},
                )

    def test_history_excludes_target_group_and_keeps_complete_panels(self) -> None:
        for row in self.prompt_rows:
            for identity in row["retrieved_panels"]:
                self.assertFalse(identity.startswith(row["heldout_study"] + ":"))
            payload = json.loads(row["user"])
            for panel in payload["retrieved_experimental_panels"]:
                self.assertGreaterEqual(len(panel["candidates"]), 2)

    def test_balanced_panel_cap_and_conditions(self) -> None:
        by_group: dict[str, set[str]] = {}
        for row in self.prompt_rows:
            by_group.setdefault(row["heldout_study"], set()).add(row["target_panel"])
        self.assertTrue(by_group)
        self.assertTrue(all(len(panels) <= 2 for panels in by_group.values()))
        self.assertEqual({row["condition"] for row in self.prompt_rows}, set(BUILDER.CONDITIONS))

    def test_checked_in_artifacts_are_current(self) -> None:
        manifest = (
            json.dumps(BUILDER.manifest(self.prompts, self.labels), indent=2, sort_keys=True) + "\n"
        )
        self.assertEqual(
            (HERE / "DOMAIN_RECORD_CONDITIONED_INPUTS.jsonl").read_bytes(), self.prompts
        )
        self.assertEqual(
            (HERE / "DOMAIN_RECORD_CONDITIONED_LABELS.jsonl").read_bytes(), self.labels
        )
        self.assertEqual((HERE / "DOMAIN_RECORD_CONDITIONED_MANIFEST.json").read_text(), manifest)

    def test_matched_baselines_cover_all_groups(self) -> None:
        artifact = json.loads((HERE / "DOMAIN_MATCHED_TEXT_BASELINE_RESULTS.json").read_text())
        self.assertEqual(artifact["artifact"], "anarres_domain_matched_text_baselines_v1")
        expected = {row["heldout_study"] for row in self.prompt_rows}
        for method in artifact["methods"].values():
            self.assertEqual({fold["heldout_study"] for fold in method["folds"]}, expected)
            self.assertGreaterEqual(method["study_macro_pairwise_ordering"], 0.0)
            self.assertLessEqual(method["study_macro_pairwise_ordering"], 1.0)


if __name__ == "__main__":
    unittest.main()
