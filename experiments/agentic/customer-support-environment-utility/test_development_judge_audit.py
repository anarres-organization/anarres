import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).parent / "scripts" / "audit_development_judge.py"
SPEC = importlib.util.spec_from_file_location("audit_development_judge", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

DECISION_SCRIPT = Path(__file__).parent / "scripts" / "record_development_judge_decision.py"
DECISION_SPEC = importlib.util.spec_from_file_location(
    "record_development_judge_decision", DECISION_SCRIPT
)
DECISION_MODULE = importlib.util.module_from_spec(DECISION_SPEC)
assert DECISION_SPEC.loader is not None
DECISION_SPEC.loader.exec_module(DECISION_MODULE)


class DevelopmentJudgeAuditTest(unittest.TestCase):
    def test_confusion_summary(self):
        summary = MODULE.summarize([(0, 0), (0, 1), (1, 0), (1, 1), (1, 1)])
        self.assertEqual(summary["agreement"], 0.6)
        self.assertEqual(summary["false_pass_rate"], 0.5)
        self.assertEqual(summary["confusion"]["official_pass_local_pass"], 2)

    def test_audit_binds_local_scores_to_frozen_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            official = root / "official" / "run1" / "task-a.json"
            local = root / "local" / "run1" / "task-a.json"
            official.parent.mkdir(parents=True)
            local.parent.mkdir(parents=True)
            official.write_text(
                json.dumps({"task_id": "task-a", "task_requirements_met": 0}),
                encoding="utf-8",
            )
            digest = MODULE.sha256(official)
            local.write_text(
                json.dumps(
                    {
                        "task_id": "task-a",
                        "official_state_bench_compatible": False,
                        "trajectory": {"sha256": digest},
                        "task_definition_sha256": "t" * 64,
                        "source_revision": "s" * 40,
                        "judge_contract": {"contract_sha256": "c" * 64},
                        "scores": {
                            "task_requirements_met": 0,
                            "task_requirements_details": [],
                        },
                    }
                ),
                encoding="utf-8",
            )
            panel = root / "panel.json"
            panel_record = {
                "status": "DEVELOPMENT_JUDGE_CALIBRATION_FROZEN",
                "source_revision": "s" * 40,
                "acceptance_gate": {
                    "task_requirement_agreement_minimum": 0.9,
                    "false_pass_rate_maximum": 0.1,
                    "automatic_qualification": False,
                    "manual_audit_required_for_every_disagreement": True,
                },
                "entries": [
                    {
                        "task_id": "task-a",
                        "task_type": "exchange_item",
                        "run_index": 1,
                        "trajectory_relative_path": "run1/task-a.json",
                        "trajectory_sha256": digest,
                        "task_definition_sha256": "t" * 64,
                    }
                ],
            }
            panel_record["panel_sha256"] = MODULE.canonical_digest(panel_record)
            panel.write_text(
                json.dumps(panel_record),
                encoding="utf-8",
            )
            output = root / "report.json"
            argv = [
                str(SCRIPT),
                "--panel",
                str(panel),
                "--official-results-dir",
                str(root / "official"),
                "--development-scores-dir",
                str(root / "local"),
                "--output",
                str(output),
            ]
            with patch.object(sys, "argv", argv):
                MODULE.main()
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "MEETS_QUANTITATIVE_GATE__MANUAL_AUDIT_REQUIRED")
            self.assertFalse(report["automatic_qualification"])

            official.write_text("{}", encoding="utf-8")
            with (
                patch.object(sys, "argv", argv),
                self.assertRaisesRegex(SystemExit, "changed after panel freeze"),
            ):
                MODULE.main()

    def test_acceptance_requires_quantitative_gate_and_manual_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "report.json"
            report.write_text(
                json.dumps(
                    {
                        "status": "MEETS_QUANTITATIVE_GATE__MANUAL_AUDIT_REQUIRED",
                        "automatic_qualification": False,
                        "panel_sha256": "p" * 64,
                        "judge_contract_sha256": "c" * 64,
                        "disagreements": [{"task_id": "task-a"}],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "decision.json"
            argv = [
                str(DECISION_SCRIPT),
                "--report",
                str(report),
                "--decision",
                "accept",
                "--output",
                str(output),
            ]
            with (
                patch.object(sys, "argv", argv),
                self.assertRaisesRegex(SystemExit, "review of every disagreement"),
            ):
                DECISION_MODULE.main()
            argv.insert(-2, "--confirm-reviewed-all-disagreements")
            with patch.object(sys, "argv", argv):
                DECISION_MODULE.main()
            decision = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(decision["status"], "ACCEPTED_FOR_TRAIN_SIDE_DEVELOPMENT")
            self.assertTrue(decision["reviewed_all_disagreements"])


if __name__ == "__main__":
    unittest.main()
