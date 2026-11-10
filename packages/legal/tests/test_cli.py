import json
import tempfile
import unittest
from pathlib import Path

from anarres.legal import cli

ROOT = Path(__file__).resolve().parents[3]


class LegalCliTest(unittest.TestCase):
    def make_lab(self, root: Path) -> Path:
        task = root / "tasks/corporate-ma/review-change-of-control"
        (task / "documents").mkdir(parents=True)
        (task / "documents/material-contract.txt").write_text("fixture", encoding="utf-8")
        (task / "task.json").write_text(
            json.dumps(
                {
                    "title": "Review change-of-control provisions",
                    "work_type": "review",
                    "tags": ["M&A", "contract-review"],
                    "instructions": "Review the matter documents and write the requested memo.",
                    "deliverables": {"memo.docx": "memo.docx"},
                    "criteria": [
                        {
                            "id": "C-001",
                            "title": "Identifies consent requirement",
                            "match_criteria": (
                                "PASS if the memo identifies the consent requirement."
                            ),
                            "deliverables": ["memo.docx"],
                            "sources": ["material-contract.txt"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return root

    def test_descriptor_is_sorted_and_side_effect_free(self) -> None:
        descriptor = cli.adapter_descriptor()
        self.assertEqual(descriptor["schema_version"], "anarres.adapter-descriptor.v1")
        self.assertEqual(descriptor["name"], "legal")
        self.assertEqual(descriptor["executable"], "anarres-legal")
        self.assertEqual(descriptor["capabilities"], sorted(set(descriptor["capabilities"])))

    def test_status_separates_syllogym_from_lab(self) -> None:
        args = type("Args", (), {"repository": ROOT})()
        result = cli.command_status(args)
        self.assertFalse(result["syllogym"]["candidate_training_outcomes_used_by_adapter"])
        self.assertEqual(result["lab"]["role"], "separate_task_regression_evaluation")
        self.assertFalse(result["lab"]["profile_input"])
        self.assertTrue(result["lab"]["workflow_intake_available"])
        self.assertFalse(result["lab"]["workflow_intake_reads_outcomes"])

    def test_profile_reuses_outcome_blind_exporter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = type(
                "Args",
                (),
                {
                    "repository": ROOT,
                    "output_dir": Path(directory),
                    "force": False,
                },
            )()
            result = cli.command_profile(args)
            profiles = [json.loads(Path(path).read_text()) for path in result["outputs"]]
        self.assertEqual(result["profile_count"], 3)
        self.assertFalse(result["outcomes_artifact_read"])
        self.assertTrue(all(profile["attributes"]["outcome_blind"] for profile in profiles))
        self.assertTrue(
            all(
                "usable_signal_density"
                not in {coordinate["name"] for coordinate in profile["coordinates"]}
                for profile in profiles
            )
        )

    def test_regression_report_reproduces_lab_without_becoming_a_profile(self) -> None:
        args = type("Args", (), {"repository": ROOT})()
        result = cli.command_regressions(args)
        self.assertEqual(result["status"], "released_reproduced")
        self.assertEqual(result["role"], "separate_task_regression_evaluation")
        self.assertFalse(result["profile_input"])
        self.assertEqual(result["support"]["severe_regressions"], 27)
        self.assertEqual(result["metrics"]["static"]["top_20pct_recall"], 0.37037037037)
        self.assertEqual(len(result["artifacts"]), 4)

    def test_lab_intake_is_model_agnostic_and_outcome_blind(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lab_root = self.make_lab(root / "lab")
            output = root / "intake"
            args = type(
                "Args",
                (),
                {
                    "repository": ROOT,
                    "lab_root": lab_root,
                    "source_revision": "fixture-revision",
                    "output_dir": output,
                    "force": False,
                },
            )()
            result = cli.command_lab_intake(args)
            summary = json.loads((output / "lab-workflow-summary.json").read_text())
            row = json.loads((output / "lab-workflow-components.jsonl").read_text())
        self.assertEqual(result["status"], "qualified")
        self.assertEqual(result["task_count"], 1)
        self.assertFalse(result["profile_input"])
        self.assertFalse(result["outcomes_artifact_read"])
        self.assertFalse(result["model_responses_read"])
        self.assertNotIn("model", row)
        self.assertEqual(summary["evaluation_contract"]["headline"], "task_all_pass")
        self.assertEqual(
            summary["evaluation_contract"]["independent_unit"], "training_intervention"
        )

    def test_verify_is_byte_deterministic(self) -> None:
        args = type("Args", (), {"repository": ROOT})()
        first = cli.command_verify(args)
        second = cli.command_verify(args)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "pass")
        self.assertFalse(first["outcomes_artifact_read"])

    def test_explicit_repository_supports_execution_outside_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                import os

                os.chdir(directory)
                result = cli.command_status(type("Args", (), {"repository": ROOT})())
            finally:
                os.chdir(previous)
        self.assertEqual(result["domain"], "legal-reasoning")


if __name__ == "__main__":
    unittest.main()
