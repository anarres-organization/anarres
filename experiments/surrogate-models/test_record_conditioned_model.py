#!/usr/bin/env python3
"""Unit checks for record-conditioned response parsing and scoring."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUNNER = load("record_runner", "run_record_conditioned_model.py")
SCORER = load("record_scorer", "score_record_conditioned_model.py")


class RecordConditionedModelTest(unittest.TestCase):
    def test_json_parser_accepts_plain_and_fenced_objects(self) -> None:
        expected = {"candidate_scores": {"C01": 0.5}}
        self.assertEqual(RUNNER.extract_json('{"candidate_scores":{"C01":0.5}}'), expected)
        self.assertEqual(
            RUNNER.extract_json('```json\n{"candidate_scores":{"C01":0.5}}\n```'), expected
        )

    def test_prediction_validation_is_strict(self) -> None:
        value = RUNNER.validate_prediction(
            {"candidate_scores": {"C01": 0.8, "C02": 0.2}, "confidence": 0.7},
            {"C01", "C02"},
        )
        self.assertEqual(value["predicted_order"], ["C01", "C02"])
        with self.assertRaises(ValueError):
            RUNNER.validate_prediction({"candidate_scores": {"C01": 1.2}}, {"C01"})

    def test_request_uses_the_frozen_reasoning_effort(self) -> None:
        payload = RUNNER.request_payload(
            "openai/gpt-oss-120b",
            {"system": "system", "user": "user"},
            8192,
            "high",
            {"C01", "C02"},
            0,
        )
        self.assertEqual(payload["reasoning_effort"], "high")
        self.assertEqual(payload["temperature"], 0)
        self.assertEqual(payload["seed"], 0)
        schema = payload["response_format"]["json_schema"]["schema"]
        self.assertEqual(schema["properties"]["candidate_scores"]["required"], ["C01", "C02"])

    def test_panel_metrics_score_selection_and_order(self) -> None:
        prediction = {
            "candidate_scores": {"C01": 0.1, "C02": 0.9},
            "abstain": False,
            "confidence": 0.8,
        }
        label = {
            "candidates": [
                {"candidate_key": "C01", "observed_normalized_utility": 0.0},
                {"candidate_key": "C02", "observed_normalized_utility": 1.0},
            ]
        }
        metrics = SCORER.panel_metrics(prediction, label)
        self.assertEqual(metrics["normalized_regret"], 0.0)
        self.assertEqual(metrics["pairwise_ordering"], 1.0)
        self.assertEqual(metrics["top_choice_credit"], 1.0)

    def test_paired_comparison_preserves_study_units(self) -> None:
        summaries = {
            "baseline": {
                "study_results": {
                    "a": {
                        "normalized_regret": 0.6,
                        "pairwise_ordering": 0.4,
                        "top_choice_credit": 0.0,
                    },
                    "b": {
                        "normalized_regret": 0.2,
                        "pairwise_ordering": 0.6,
                        "top_choice_credit": 0.5,
                    },
                }
            },
            "candidate": {
                "study_results": {
                    "a": {
                        "normalized_regret": 0.1,
                        "pairwise_ordering": 0.9,
                        "top_choice_credit": 1.0,
                    },
                    "b": {
                        "normalized_regret": 0.2,
                        "pairwise_ordering": 0.6,
                        "top_choice_credit": 0.5,
                    },
                }
            },
        }
        comparison = SCORER.paired_comparison(summaries, "baseline", "candidate")
        self.assertEqual(comparison["independent_studies"], 2)
        regret = comparison["normalized_regret_improvement"]
        self.assertAlmostEqual(regret["mean"], 0.25)
        self.assertEqual(regret["studies_improved"], 1)
        self.assertEqual(regret["studies_tied"], 1)


if __name__ == "__main__":
    unittest.main()
