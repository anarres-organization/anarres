"""Tests for the formal-verification source-qualification records."""

from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "formal_verification_source_qualification", ROOT / "scripts" / "verify.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def source(record: dict, source_id: str) -> dict:
    return next(item for item in record["sources"] if item["source_id"] == source_id)


class SourceQualificationTest(unittest.TestCase):
    """Check reproduction, decision logic, and tamper rejection."""

    def setUp(self) -> None:
        self.sources, self.qualification, self.matrix = MODULE.load_records()

    def errors(self) -> list[str]:
        return MODULE.validate(self.sources, self.qualification, self.matrix)

    def test_records_validate(self) -> None:
        self.assertEqual(self.errors(), [])

    def test_reproduces_committed_summary(self) -> None:
        expected = (ROOT / "results" / "summary.json").read_text(encoding="utf-8")
        actual = MODULE.canonical_json(
            MODULE.compute_summary(
                self.sources, self.qualification, self.matrix, MODULE.input_digests()
            )
        )
        self.assertEqual(actual, expected)

    def selection_checks(self, record: dict) -> set[str]:
        return {gate["id"] for gate in record["gate"] if gate["tier"] == "source_selection"}

    def promote(self, record: dict, source_id: str) -> dict:
        """Promote a source the honest way: close its blockers with confirmed evidence."""
        item = source(record, source_id)
        selection = self.selection_checks(record)
        for check_id in selection:
            item["checks"][check_id] = {
                "status": "pass",
                "evidence": [{"claim": "closed by a later smoke test", "basis": "confirmed"}],
            }
        item["unresolved_checks"] = [
            entry for entry in item["unresolved_checks"] if entry["check"] not in selection
        ]
        item["decision"] = "proceed"
        return item

    def test_recommendation_follows_the_selection_rule(self) -> None:
        computed = MODULE.compute_recommendation(self.qualification)
        recorded = self.qualification["recommendation"]
        for key, value in computed.items():
            self.assertEqual(recorded[key], value)
        decisions = {
            item["source_id"]: MODULE.derive_decision(self.qualification, item)
            for item in self.qualification["sources"]
        }
        self.assertNotIn("proceed", decisions.values())
        self.assertEqual(computed["outcome"], "abstain")
        self.assertEqual(computed["leading_candidate"], computed["reserve_ranking"][0])

    def test_rule_selects_once_blockers_close_and_abstains_otherwise(self) -> None:
        leading = MODULE.compute_recommendation(self.qualification)["leading_candidate"]
        self.assertEqual(MODULE.compute_recommendation(self.qualification)["outcome"], "abstain")
        promoted = copy.deepcopy(self.qualification)
        self.promote(promoted, leading)
        computed = MODULE.compute_recommendation(promoted)
        self.assertEqual(computed["outcome"], "select")
        self.assertEqual(computed["selected_source"], leading)
        self.assertNotIn(leading, computed["reserve_ranking"])
        self.qualification = promoted
        self.assertTrue(any("recommendation outcome" in error for error in self.errors()))

    def test_tamper_a_flipping_statuses_cannot_promote_a_source(self) -> None:
        selection = self.selection_checks(self.qualification)
        for item in self.qualification["sources"]:
            tampered = copy.deepcopy(self.qualification)
            target = source(tampered, item["source_id"])
            for check_id in selection:
                target["checks"][check_id]["status"] = "pass"
            target["decision"] = "proceed"
            errors = MODULE.validate(self.sources, tampered, self.matrix)
            self.assertTrue(errors, item["source_id"])
            self.assertTrue(
                any("cannot pass while this entry is open" in error for error in errors)
                or any("confirmed evidence" in error for error in errors),
                item["source_id"],
            )

    def test_tamper_b_unknown_evidence_and_wrong_tier_blocker(self) -> None:
        selection = self.selection_checks(self.qualification)
        item = next(
            candidate
            for candidate in self.qualification["sources"]
            if any(candidate["checks"][check]["status"] != "pass" for check in selection)
        )
        check_id = next(
            check for check in sorted(selection) if item["checks"][check]["status"] != "pass"
        )
        item["checks"][check_id] = {
            "status": "pass",
            "evidence": [{"claim": "assumed to hold", "basis": "unknown"}],
        }
        item["unresolved_checks"] = [
            entry for entry in item["unresolved_checks"] if entry["check"] != check_id
        ]
        item["unresolved_checks"].append(
            {
                "id": "tamper-b",
                "check": check_id,
                "blocks": "panel_freeze",
                "basis": "confirmed",
                "text": "relabeled as a later concern",
            }
        )
        errors = self.errors()
        self.assertTrue(any("needs at least one confirmed" in error for error in errors))
        self.assertTrue(any("blocks 'panel_freeze' but" in error for error in errors))

    def test_proceed_with_failed_gate_is_rejected(self) -> None:
        selection = self.selection_checks(self.qualification)
        item = next(
            candidate
            for candidate in self.qualification["sources"]
            if any(candidate["checks"][check]["status"] == "fail" for check in selection)
        )
        item["decision"] = "proceed"
        self.assertTrue(any("differs from derived decision" in error for error in self.errors()))

    def test_failure_without_remediation_derives_reject(self) -> None:
        leading = MODULE.compute_recommendation(self.qualification)["leading_candidate"]
        item = source(self.qualification, leading)
        item["checks"]["verifier_reproduced"]["status"] = "fail"
        item["checks"]["verifier_reproduced"].pop("remediation", None)
        self.assertEqual(MODULE.derive_decision(self.qualification, item), "reject")
        self.assertTrue(any("derived decision 'reject'" in error for error in self.errors()))

    def test_source_dropped_from_one_file_is_rejected(self) -> None:
        self.matrix["sources"] = [
            item for item in self.matrix["sources"] if item["source_id"] != "verisoftbench"
        ]
        self.assertTrue(any("CANDIDATE_MATRIX sources" in error for error in self.errors()))

    def test_unknown_decision_is_rejected(self) -> None:
        source(self.qualification, "oss-verify")["decision"] = "maybe"
        self.assertTrue(any("unknown decision" in error for error in self.errors()))

    def test_reserve_requires_unresolved_checks(self) -> None:
        source(self.qualification, "oss-verify")["unresolved_checks"] = []
        self.assertTrue(any("requires unresolved_checks" in error for error in self.errors()))

    def test_proceed_lists_every_open_panel_freeze_check(self) -> None:
        leading = MODULE.compute_recommendation(self.qualification)["leading_candidate"]
        item = self.promote(self.qualification, leading)
        item["unresolved_checks"] = [
            entry for entry in item["unresolved_checks"] if entry["blocks"] != "panel_freeze"
        ]
        self.assertTrue(any("has no unresolved entry" in error for error in self.errors()))

    def test_claim_basis_cannot_be_relabeled(self) -> None:
        claim = source(self.qualification, "vero")["checks"]["policy_headroom"]["evidence"][0]
        claim["basis"] = "established"
        self.assertTrue(any("basis must be one of" in error for error in self.errors()))

    def test_recorded_recommendation_must_match_rule(self) -> None:
        ranking = self.qualification["recommendation"]["reserve_ranking"]
        self.qualification["recommendation"]["leading_candidate"] = ranking[-1]
        self.assertTrue(any("leading_candidate" in error for error in self.errors()))

    def test_smoke_tests_and_pilots_follow_their_rules(self) -> None:
        recommendation = self.qualification["recommendation"]
        self.assertEqual(len(recommendation["smoke_tests"]), 2)
        tampered = copy.deepcopy(self.qualification)
        tampered["recommendation"]["smoke_tests"].reverse()
        errors = MODULE.validate(self.sources, tampered, self.matrix)
        self.assertTrue(any("smoke-test rule" in error for error in errors))
        recommendation["policy_pilots"] = []
        self.assertTrue(any("policy-pilot rule" in error for error in self.errors()))

    def test_proposed_decisions_do_not_open_outcomes(self) -> None:
        for item in self.matrix["sources"]:
            self.assertFalse(item["proposed_held_out_decision"]["outcome_opened"])
            self.assertTrue(item["visible_published_outcomes"])

    def test_endpoints_are_never_pooled(self) -> None:
        self.qualification["endpoint_pooling_allowed"] = True
        self.assertTrue(any("never be pooled" in error for error in self.errors()))

    def test_conflicted_survey_entry_cannot_be_selected(self) -> None:
        entries = self.qualification["fifth_source_survey"]["entries"]
        veribench = next(entry for entry in entries if entry["name"] == "VeriBench")
        self.assertIn("independent auditor", veribench["conflict_of_interest"])
        veribench["call"] = "selected"
        self.assertTrue(any("conflicted source selected" in error for error in self.errors()))

    def test_no_host_paths_or_credentials(self) -> None:
        self.assertEqual(MODULE.scan_directory(), [])
        planted = {
            "home.json": "/" + "Users/alice/data",
            "cluster.md": "ran on " + "skam" + "pere3",
            "token.json": "s" + "k-" + "a" * 24,
            "key.json": "api" + "_key = abc",
        }
        self.assertEqual(len(MODULE.scan_texts(planted)), 4)

    def test_qualification_uses_only_released_piggybank_evidence(self) -> None:
        item = next(
            entry
            for entry in source(self.qualification, "vero")["unresolved_checks"]
            if entry["id"] == "vero-piggybank-axiom"
        )
        self.assertEqual(item["basis"], "confirmed")
        self.assertNotIn("unreleased proof workspace", item["text"])
        self.assertIn("do not establish whether submitted proofs used", item["text"])


if __name__ == "__main__":
    unittest.main()
