"""Scientific-integrity tests for the formal-verification evidence record."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "formal_verification_reproduce", ROOT / "scripts" / "reproduce.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class EvidenceRecordTest(unittest.TestCase):
    """Check derived values, chronology, and claim boundaries."""

    def load(self, name: str) -> dict[str, object]:
        return json.loads((ROOT / "data" / name).read_text())

    def test_reproduces_committed_summary(self) -> None:
        expected = (ROOT / "results" / "summary.json").read_text()
        self.assertEqual(MODULE.canonical_json(MODULE.compute()), expected)

    def test_no_retrospective_record_is_labeled_prospective(self) -> None:
        for name in ("verusyn.json", "reform.json", "formal-disco.json"):
            record = self.load(name)
            self.assertFalse(record["chronology"]["chronologically_prospective"])

    def test_verusyn_panels_preserve_native_targets(self) -> None:
        record = self.load("verusyn.json")
        targets = {panel["target"] for panel in record["panels"]}
        self.assertEqual(targets, {"algorithmic", "system"})
        self.assertEqual(MODULE.verusyn_score(record)["top_choice_correct"], 7)

    def test_raw_verifier_rule_is_retained_as_a_falsification(self) -> None:
        score = MODULE.reform_score(self.load("reform.json"))
        self.assertEqual(score["raw_verifier_top_choice_correct"], 0)
        self.assertGreater(score["raw_verifier_mean_semantic_regret_pp"], 0)

    def test_cross_policy_disagreement_is_not_repeated_coverage(self) -> None:
        record = self.load("vericoding.json")
        boundaries = " ".join(record["claim_boundary"])
        self.assertIn("rather than repeated sampling", boundaries)

    def test_policy_scores_remain_contract_specific(self) -> None:
        record = self.load("policy-support.json")
        score = MODULE.policy_support_score(record)
        self.assertEqual(score["leanlean_compression_leader"], "Opus 5 with Claude Code")
        self.assertEqual(
            score["vero_code_and_proof_leader"],
            "GPT-5.5 xhigh with Codex 0.140.0",
        )
        self.assertFalse(score["uniform_policy_leader_across_contracts"])

    def test_policy_record_does_not_mandate_gpt_5_6(self) -> None:
        record = self.load("policy-support.json")
        boundary = record["selection_boundary"]
        self.assertIn("one locally executable", boundary["current_qualification"])
        self.assertIn("does not", boundary["not_established"])
        self.assertIn("policy panel", boundary["next_decision"])

    def test_same_policy_boundary_support_is_not_cross_policy_disagreement(self) -> None:
        record = self.load("policy-support.json")
        boundary = record["sources"]["forall_verisoftbench"]["same_policy_boundary_evidence"]
        self.assertEqual(boundary["configuration_id"], "codex_sol_xhigh")
        self.assertEqual(boundary["target_protocol"], "Pass@8, r=3")
        self.assertEqual(boundary["tasks_solved_after_sample_one"], 15)
        self.assertTrue(all(task["solved_on_sample"] > 1 for task in boundary["boundary_tasks"]))
        self.assertIn("do not expose", boundary["interpretation"])

    def test_article_and_public_proof_counts_remain_distinct(self) -> None:
        record = self.load("anthropic-oss-fuzz.json")
        self.assertEqual(record["production_result"]["proved_entry_points"], 239)
        self.assertEqual(record["public_proof_release"]["proved_entry_points"], 90)
        self.assertFalse(record["public_proof_release"]["semantics_complete"])

    def test_source_revisions_are_pinned(self) -> None:
        sources = json.loads((ROOT / "SOURCES.json").read_text())["sources"]
        revisioned = [
            source for source in sources if "repository" in source or "revision" in source
        ]
        self.assertTrue(revisioned)
        for source in revisioned:
            self.assertRegex(source["revision"], r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
