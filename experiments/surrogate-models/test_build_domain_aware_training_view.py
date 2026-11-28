#!/usr/bin/env python3
"""Checks for the domain-aware utility training view."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_domain_aware_training_view", HERE / "build_domain_aware_training_view.py"
)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


class DomainAwareTrainingViewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inputs = read_jsonl(HERE / "DOMAIN_AWARE_UTILITY_INPUTS.jsonl")
        cls.labels = read_jsonl(HERE / "DOMAIN_AWARE_UTILITY_LABELS.jsonl")
        cls.splits = json.loads((HERE / "DOMAIN_AWARE_NESTED_SPLITS.json").read_text())
        cls.manifest = json.loads((HERE / "DOMAIN_AWARE_TRAINING_VIEW.json").read_text())

    def test_generated_artifacts_are_current(self) -> None:
        for path, content in BUILDER.build().items():
            self.assertEqual(path.read_bytes(), content)

    def test_candidate_aggregation_preserves_all_records(self) -> None:
        self.assertEqual(len(self.inputs), 3665)
        self.assertEqual(len(self.labels), 3665)
        self.assertEqual(sum(row["scoring"]["training_runs"] for row in self.labels), 3713)
        self.assertEqual(self.manifest["utility"]["panels"], 985)
        self.assertEqual(self.manifest["utility"]["studies"], 51)

    def test_inputs_and_labels_have_an_exact_opaque_join(self) -> None:
        input_keys = {row["candidate_key"] for row in self.inputs}
        label_keys = {row["candidate_key"] for row in self.labels}
        self.assertEqual(input_keys, label_keys)
        for row in self.inputs:
            self.assertTrue(row["candidate_key"].startswith("candidate-"))
            self.assertTrue(row["partition"]["panel_key"].startswith("panel-"))
            self.assertTrue(row["partition"]["study_key"].startswith("study-"))

    def test_protected_outcomes_are_absent_from_feature_views(self) -> None:
        forbidden = ("native_mean", "normalized_utility", "record_join_keys")
        for row in self.inputs:
            rendered = json.dumps(row["feature_views"], sort_keys=True)
            for token in forbidden:
                self.assertNotIn(token, rendered)

    def test_missing_modalities_are_not_invented(self) -> None:
        for row in self.inputs:
            modalities = row["modalities"]
            self.assertFalse(modalities["code"])
            self.assertFalse(modalities["curves"])
            self.assertFalse(modalities["trajectories"])
            self.assertFalse(modalities["perceptual_or_structural_assets"])

    def test_outer_and_inner_history_never_include_their_holdout(self) -> None:
        for suite in self.splits["suites"]:
            for outer in suite["folds"]:
                self.assertEqual(
                    outer["train_candidate_keys_sha256"],
                    outer["retrieval_history_candidate_keys_sha256"],
                )
                self.assertGreater(outer["train_candidates"], 0)
                self.assertGreater(outer["test_candidates"], 0)
                for inner in outer["inner_folds"]:
                    self.assertEqual(
                        inner["train_candidate_keys_sha256"],
                        inner["retrieval_history_candidate_keys_sha256"],
                    )
                    self.assertGreater(inner["train_candidates"], 0)
                    self.assertGreater(inner["validation_candidates"], 0)


if __name__ == "__main__":
    unittest.main()
