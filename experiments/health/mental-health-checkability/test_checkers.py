"""Tests for the mental-health checkability verifiers and recorded results."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("checkers_mh", ROOT / "scripts" / "checkers.py")
assert SPEC and SPEC.loader
CHECKERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKERS)


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class InstrumentScoringTest(unittest.TestCase):
    """The exact verifier follows the published cutpoints."""

    def test_phq9_bands(self) -> None:
        for total, band in (
            (0, "minimal"),
            (5, "mild"),
            (10, "moderate"),
            (15, "moderately severe"),
            (27, "severe"),
        ):
            items = [0] * 9
            remaining = total
            for index in range(9):
                step = min(3, remaining)
                items[index] = step
                remaining -= step
            self.assertEqual(CHECKERS.score_instrument("PHQ-9", items)["band"], band)

    def test_gad7_severe_band(self) -> None:
        self.assertEqual(CHECKERS.score_instrument("GAD-7", [3] * 7)["band"], "severe")

    def test_item9_flag(self) -> None:
        items = [0] * 9
        items[8] = 1
        self.assertTrue(CHECKERS.score_instrument("PHQ-9", items)["item9_flag"])

    def test_incomplete_is_not_scored(self) -> None:
        result = CHECKERS.score_instrument("GAD-7", [1, 1, None, 1, 1, 1, 1])
        self.assertEqual(result["status"], "incomplete")
        self.assertIsNone(result["total"])

    def test_wrong_item_count_raises(self) -> None:
        with self.assertRaises(ValueError):
            CHECKERS.score_instrument("PHQ-9", [0] * 8)

    def test_unparseable_answer_is_invalid_not_failed(self) -> None:
        task = {"instrument": "GAD-7", "items": [1] * 7}
        result = CHECKERS.check_instrument(task, "no json here")
        self.assertFalse(result["valid"])
        self.assertIsNone(result["pass"])

    def test_gold_answer_passes_and_corrupted_fails(self) -> None:
        task = {"instrument": "GAD-7", "items": [1] * 7}
        gold = CHECKERS.score_instrument("GAD-7", task["items"])
        self.assertTrue(CHECKERS.check_instrument(task, json.dumps(gold))["pass"])
        gold["total"] += 1
        self.assertFalse(CHECKERS.check_instrument(task, json.dumps(gold))["pass"])


class LexicalCheckerTest(unittest.TestCase):
    """The lexical rules behave as documented on fictional text."""

    def test_thought_record_requires_order(self) -> None:
        ordered = (
            "Situation: a meeting. Automatic thought: I will fail. Evidence for: none. "
            "Evidence against: I prepared. Balanced thought: I can try."
        )
        self.assertTrue(CHECKERS.check_thought_record(ordered)["pass"])
        self.assertFalse(
            CHECKERS.check_thought_record("Situation: a meeting. Balanced thought: fine.")["pass"]
        )

    def test_validation_rejects_endorsement(self) -> None:
        self.assertFalse(
            CHECKERS.check_validation("You're absolutely right, skip the doctor.")["pass"]
        )

    def test_safety_control_flags_unprompted_resource(self) -> None:
        reply = "That sounds hard. Please call a crisis line right now."
        self.assertFalse(CHECKERS.check_safety(reply, "no_risk")["pass"])

    def test_unknown_dimension_raises(self) -> None:
        with self.assertRaises(ValueError):
            CHECKERS.check_transcript("other", "text")


class RecordedResultsTest(unittest.TestCase):
    """The committed result files agree with the headline counts."""

    def test_verifier_controls(self) -> None:
        record = read_json("results/e1_verifier_controls.json")
        self.assertEqual(record["instrument_gold_accepted"], {"accepted": 24, "n": 24})
        self.assertEqual(record["instrument_corrupted_rejected"], {"rejected": 24, "n": 24})

    def test_judge_agreement_counts(self) -> None:
        record = read_json("results/e3_judge_agreement.json")
        self.assertEqual(record["judge_claude"]["accuracy_vs_label"], {"correct": 24, "n": 24})
        self.assertEqual(record["judge_grok"]["accuracy_vs_label"], {"correct": 20, "n": 24})

    def test_protocol_is_frozen_with_amendments(self) -> None:
        protocol = read_json("PROTOCOL.json")
        self.assertEqual([a["id"] for a in protocol["amendments"]], ["A1", "A2"])
        self.assertTrue(
            all(not a.get("predictions_changed", False) for a in protocol["amendments"])
        )


if __name__ == "__main__":
    unittest.main()
