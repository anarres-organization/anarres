#!/usr/bin/env python3
"""Checks for the separated surrogate model views."""

from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("build_model_views", HERE / "build_model_views.py")
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


def walk_keys(value: object) -> list[str]:
    if isinstance(value, dict):
        return list(value) + [key for child in value.values() for key in walk_keys(child)]
    if isinstance(value, list):
        return [key for child in value for key in walk_keys(child)]
    return []


def walk_strings(value: object) -> list[str]:
    if isinstance(value, dict):
        return [item for child in value.values() for item in walk_strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in walk_strings(child)]
    return [value] if isinstance(value, str) else []


class ModelViewsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = BUILDER.read_records()
        cls.inputs, cls.labels = BUILDER.render(cls.records)
        cls.input_rows = [json.loads(line) for line in cls.inputs.splitlines()]
        cls.label_rows = [json.loads(line) for line in cls.labels.splitlines()]

    def test_views_cover_the_frozen_corpus(self) -> None:
        self.assertEqual(len(self.input_rows), 3641)
        self.assertEqual(len(self.label_rows), 3641)
        self.assertEqual(
            [row["join_key"] for row in self.input_rows],
            [row["join_key"] for row in self.label_rows],
        )
        self.assertEqual(len({row["join_key"] for row in self.input_rows}), 3641)

    def test_outcomes_and_scoring_identities_are_not_features(self) -> None:
        for row in self.input_rows:
            self.assertEqual(set(row), {"join_key", "features"})
            self.assertRegex(row["join_key"], r"^record-[0-9a-f]{24}$")
            keys = walk_keys(row["features"])
            self.assertNotIn("outcome", keys)
            self.assertFalse(any(BUILDER.forbidden_key(key) for key in keys))
            self.assertFalse(
                any(
                    re.fullmatch(r"(?:[0-9a-fA-F]{32,128}|sha256:[0-9a-fA-F]{64})", value)
                    for value in walk_strings(row["features"])
                )
            )

    def test_native_frozen_decisions_are_not_features(self) -> None:
        for row in self.input_rows:
            keys = walk_keys(row["features"])
            self.assertNotIn("point_prediction", keys)
            self.assertNotIn("selected_candidate", keys)

    def test_realized_training_costs_are_not_features(self) -> None:
        for row in self.input_rows:
            cost = row["features"]["cost"]
            self.assertLessEqual(set(cost), {"sample_count"})
            self.assertNotIn("generated_action_tokens", cost)
            self.assertNotIn("admitted_tokens", cost)

    def test_native_measurements_remain_namespaced(self) -> None:
        def with_key(domain: str, key: str) -> dict[str, object]:
            return next(
                row
                for row in self.input_rows
                if row["features"]["domain"] == domain and key in row["features"]["prediction_time"]
            )

        self.assertIn(
            "rho_per_million_generated_tokens",
            with_key("mathematics", "rho_per_million_generated_tokens")["features"][
                "prediction_time"
            ],
        )
        self.assertIn(
            "candidate_measurement",
            with_key("robotics", "candidate_measurement")["features"]["prediction_time"],
        )
        self.assertIn(
            "allocation_weights",
            with_key("legal", "allocation_weights")["features"]["prediction_time"],
        )

    def test_labels_retain_native_outcomes(self) -> None:
        self.assertTrue(all("outcome" in row for row in self.label_rows))
        self.assertTrue(all("candidate_id" in row["scoring"] for row in self.label_rows))

    def test_checked_in_views_are_current(self) -> None:
        self.assertEqual((HERE / "MODEL_INPUTS.jsonl").read_bytes(), self.inputs)
        self.assertEqual((HERE / "MODEL_LABELS.jsonl").read_bytes(), self.labels)
        checked = json.loads((HERE / "MODEL_VIEWS.json").read_text())
        self.assertEqual(checked, BUILDER.build_manifest(self.records, self.inputs, self.labels))


if __name__ == "__main__":
    unittest.main()
