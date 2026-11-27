#!/usr/bin/env python3
"""Checks for record-conditioned replay inputs and protected labels."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "record_builder", HERE / "build_record_conditioned_replay.py"
)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BUILDER
SPEC.loader.exec_module(BUILDER)


class RecordConditionedReplayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prompts = BUILDER.read_jsonl(BUILDER.PROMPTS)
        cls.labels = {row["prompt_id"]: row for row in BUILDER.read_jsonl(BUILDER.TARGETS)}

    def test_artifacts_rebuild_exactly(self) -> None:
        prompts, labels = BUILDER.render()
        self.assertEqual(prompts, BUILDER.PROMPTS.read_bytes())
        self.assertEqual(labels, BUILDER.TARGETS.read_bytes())

    def test_all_conditions_cover_the_same_panels(self) -> None:
        panels = {}
        for condition in BUILDER.CONDITIONS:
            panels[condition] = {
                (row["heldout_study"], row["target_panel"])
                for row in self.prompts
                if row["condition"] == condition
            }
        self.assertEqual(len({frozenset(value) for value in panels.values()}), 1)
        self.assertEqual(len(next(iter(panels.values()))), 9)

    def test_target_outcomes_do_not_enter_prompts(self) -> None:
        for prompt in self.prompts:
            payload = json.loads(prompt["user"])
            self.assertNotIn("observed_outcome", json.dumps(payload["target_candidates"]))
            for history in payload["permitted_cross_study_history"]:
                self.assertNotEqual(
                    history["environment"]["title"], payload["target_environment"]["title"]
                )

    def test_history_and_measurement_ablations_are_exact(self) -> None:
        for prompt in self.prompts:
            payload = json.loads(prompt["user"])
            expect_history = prompt["condition"].startswith("cross_history")
            expect_measurements = prompt["condition"].endswith("with_measurements")
            self.assertEqual(bool(payload["permitted_cross_study_history"]), expect_history)
            for candidate in payload["target_candidates"]:
                self.assertEqual("prediction_time_measurements" in candidate, expect_measurements)
            for history in payload["permitted_cross_study_history"]:
                self.assertEqual(
                    "prediction_time_measurements" in history["intervention"], expect_measurements
                )

    def test_prompt_and_label_keys_match(self) -> None:
        self.assertEqual({row["prompt_id"] for row in self.prompts}, set(self.labels))
        for prompt in self.prompts:
            payload = json.loads(prompt["user"])
            expected = {row["candidate_key"] for row in payload["target_candidates"]}
            observed = {
                row["candidate_key"] for row in self.labels[prompt["prompt_id"]]["candidates"]
            }
            self.assertEqual(expected, observed)

    def test_prediction_receipt_and_runtime_bind_released_outputs(self) -> None:
        predictions = HERE / "RECORD_CONDITIONED_PREDICTIONS.jsonl"
        receipt_path = HERE / "RECORD_CONDITIONED_PREDICTION_RECEIPT.json"
        receipt = json.loads(receipt_path.read_text())
        runtime = json.loads((HERE / "RECORD_CONDITIONED_RUNTIME.json").read_text())
        results = json.loads((HERE / "RECORD_CONDITIONED_RESULTS.json").read_text())
        digest = hashlib.sha256(predictions.read_bytes()).hexdigest()
        self.assertEqual(receipt["rows"], 36)
        self.assertEqual(receipt["predictions_sha256"], digest)
        self.assertEqual(runtime["outputs"]["predictions_sha256"], digest)
        self.assertEqual(results["inputs"]["predictions_sha256"], digest)
        rows = [json.loads(line) for line in predictions.read_text().splitlines()]
        self.assertEqual(len({row["prompt_id"] for row in rows}), 36)
        self.assertEqual(sum(len(row["usage"]["attempts"]) for row in rows), 36)


if __name__ == "__main__":
    unittest.main()
