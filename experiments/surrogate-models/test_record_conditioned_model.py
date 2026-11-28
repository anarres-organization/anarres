#!/usr/bin/env python3
"""Unit checks for record-conditioned response parsing and scoring."""

from __future__ import annotations

import importlib.util
import json
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
DOMAIN_SCORER = load("domain_record_scorer", "score_domain_record_conditioned_model.py")


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

    def test_neutral_abstention_penalizes_exhausted_serving_failure(self) -> None:
        prediction = RUNNER.neutral_abstention({"C02", "C01"}, "no final JSON")
        self.assertEqual(prediction["candidate_scores"], {"C01": 0.5, "C02": 0.5})
        self.assertEqual(prediction["predicted_order"], ["C01", "C02"])
        self.assertTrue(prediction["abstain"])
        self.assertEqual(prediction["confidence"], 0.0)
        self.assertIn("no final JSON", prediction["evidence_summary"])

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

    def test_domain_summary_keeps_studies_as_the_unit(self) -> None:
        results = {
            "legal-a": {
                "panels": 2,
                "normalized_regret": 0.2,
                "pairwise_ordering": 0.8,
                "top_choice_credit": 0.5,
                "confidence": 0.6,
                "abstention": 0.0,
            },
            "legal-b": {
                "panels": 1,
                "normalized_regret": 0.4,
                "pairwise_ordering": 0.6,
                "top_choice_credit": 1.0,
                "confidence": 0.8,
                "abstention": 1.0,
            },
        }
        summary = DOMAIN_SCORER.summarize_domains(
            results, {"legal-a": "legal", "legal-b": "legal"}
        )["legal"]
        self.assertEqual(summary["studies"], 2)
        self.assertEqual(summary["panels"], 3)
        self.assertAlmostEqual(summary["study_macro_normalized_regret"], 0.3)
        self.assertAlmostEqual(summary["study_macro_pairwise_ordering"], 0.7)
        self.assertAlmostEqual(summary["study_macro_abstention"], 0.5)

    def test_domain_comparison_filters_complete_studies(self) -> None:
        def row(regret: float, order: float) -> dict:
            return {
                "normalized_regret": regret,
                "pairwise_ordering": order,
                "top_choice_credit": order,
            }

        summaries = {
            "baseline": {"study_results": {"legal": row(0.8, 0.4), "robotics": row(0.6, 0.5)}},
            "candidate": {"study_results": {"legal": row(0.3, 0.7), "robotics": row(0.2, 0.9)}},
        }
        comparisons = DOMAIN_SCORER.paired_comparison_by_domain(
            summaries,
            "baseline",
            "candidate",
            {"legal": "legal", "robotics": "robotics"},
        )
        self.assertEqual(comparisons["legal"]["independent_studies"], 1)
        self.assertAlmostEqual(comparisons["legal"]["normalized_regret_improvement"]["mean"], 0.5)
        self.assertAlmostEqual(
            comparisons["robotics"]["pairwise_ordering_improvement"]["mean"], 0.4
        )

    def test_released_domain_predictions_match_the_receipt(self) -> None:
        predictions = HERE / "DOMAIN_RECORD_CONDITIONED_PREDICTIONS.jsonl"
        receipt_path = HERE / "DOMAIN_RECORD_CONDITIONED_PREDICTION_RECEIPT.json"
        receipt = json.loads(receipt_path.read_text())
        self.assertEqual(receipt["rows"], 356)
        self.assertEqual(receipt["predictions_sha256"], RUNNER.sha256(predictions))
        self.assertEqual(
            receipt["contract_sha256"],
            RUNNER.sha256(HERE / "DOMAIN_RECORD_CONDITIONED_CONTRACT.json"),
        )
        self.assertEqual(
            receipt["inputs_sha256"],
            RUNNER.sha256(HERE / "DOMAIN_RECORD_CONDITIONED_INPUTS.jsonl"),
        )

    def test_released_domain_results_cover_every_condition_and_domain(self) -> None:
        results = json.loads((HERE / "DOMAIN_RECORD_CONDITIONED_RESULTS.json").read_text())
        self.assertEqual(
            set(results["conditions"]),
            {
                "zero_history_without_measurements",
                "retrieved_history_without_measurements",
                "zero_history_with_measurements",
                "retrieved_history_with_measurements",
            },
        )
        expected_domains = {
            "agentic_coding",
            "finance",
            "legal",
            "materials_science",
            "robotics",
        }
        for summary in results["conditions"].values():
            self.assertEqual(summary["panels"], 89)
            self.assertEqual(summary["studies"], 51)
            self.assertEqual(set(summary["domain_results"]), expected_domains)


if __name__ == "__main__":
    unittest.main()
