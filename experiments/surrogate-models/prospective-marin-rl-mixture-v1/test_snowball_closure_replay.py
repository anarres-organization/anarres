#!/usr/bin/env python3
"""Tests for the public Snowball multi-target replay."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_snowball_closure_replay", HERE / "build_snowball_closure_replay.py"
)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


class SnowballClosureReplayTest(unittest.TestCase):
    def setUp(self) -> None:
        self.inputs = read_jsonl(HERE / "SNOWBALL_CLOSURE_INPUTS.jsonl")
        self.labels = read_jsonl(HERE / "SNOWBALL_CLOSURE_PROTECTED_LABELS.jsonl")
        self.manifest = json.loads((HERE / "SNOWBALL_CLOSURE_REPLAY.json").read_text())

    def test_generated_artifacts_are_current(self) -> None:
        for path, content in BUILDER.build().items():
            self.assertEqual(path.read_bytes(), content)

    def test_one_row_means_one_trained_intervention(self) -> None:
        self.assertEqual(len(self.inputs), 3)
        self.assertEqual(len(self.labels), 3)
        self.assertEqual(len({row["record_key"] for row in self.inputs}), 3)
        self.assertEqual(self.manifest["summary"]["trained_interventions"], 3)
        self.assertEqual(self.manifest["summary"]["nested_capability_targets"], 4)
        self.assertEqual(self.manifest["summary"]["serving_repeats_per_target"], 6)

    def test_inputs_do_not_contain_protected_outcomes(self) -> None:
        encoded = json.dumps(self.inputs, sort_keys=True)
        self.assertNotIn("candidate_mean", encoded)
        self.assertNotIn("change", encoded)
        self.assertNotIn("outcomes", encoded)
        self.assertEqual(
            {row["record_key"] for row in self.inputs},
            {row["record_key"] for row in self.labels},
        )

    def test_starting_policy_measurements_are_shared(self) -> None:
        measurements = {
            json.dumps(row["prediction_time"]["starting_policy_measurements"], sort_keys=True)
            for row in self.inputs
        }
        self.assertEqual(len(measurements), 1)

    def test_regressions_remain_target_specific(self) -> None:
        regressions = [
            (row["record_key"], outcome["metric"])
            for row in self.labels
            for outcome in row["outcomes"]
            if outcome["change"] < 0
        ]
        self.assertEqual(len(regressions), 4)
        self.assertTrue(any(metric == "math500" for _, metric in regressions))

    def test_mochi_is_absent_and_uneven_modalities_stay_closed(self) -> None:
        self.assertNotIn("mochi", json.dumps([self.inputs, self.labels]).lower())
        for row in self.inputs:
            self.assertFalse(row["modalities"]["trajectories"])
            self.assertFalse(row["modalities"]["curves"])


if __name__ == "__main__":
    unittest.main()
