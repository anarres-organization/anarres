import json
import os
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / "target/debug/anarres"


@unittest.skipUnless(os.name == "posix", "executable-wrapper test requires POSIX")
class LegalCliCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        if not BINARY.is_file():
            subprocess.run(
                ["cargo", "build", "--quiet", "-p", "anarres-cli"],
                cwd=ROOT,
                check=True,
            )

    def wrapper(self, directory: Path) -> Path:
        path = directory / "anarres-legal"
        path.write_text(
            f'#!/bin/sh\nexec {shlex.quote(sys.executable)} -m anarres.legal.cli "$@"\n',
            encoding="utf-8",
        )
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def run_cli(self, directory: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PATH"] = os.pathsep.join([str(directory), environment.get("PATH", "")])
        source_paths = [
            ROOT / "packages/legal/src",
            ROOT / "packages/environments/src",
            ROOT / "packages/core/src",
        ]
        environment["PYTHONPATH"] = os.pathsep.join(str(path) for path in source_paths)
        return subprocess.run(
            [str(BINARY), *arguments],
            cwd=directory,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def make_lab(self, root: Path) -> Path:
        task = root / "tasks/litigation/draft-case-memo"
        (task / "documents").mkdir(parents=True)
        (task / "documents/record.txt").write_text("fixture", encoding="utf-8")
        (task / "task.json").write_text(
            json.dumps(
                {
                    "title": "Draft a case memo",
                    "work_type": "draft",
                    "tags": ["litigation"],
                    "instructions": "Review the record and draft the memo.",
                    "deliverables": {"memo.docx": "memo.docx"},
                    "criteria": [
                        {
                            "id": "C-001",
                            "title": "Grounds the conclusion",
                            "match_criteria": "PASS if the conclusion is grounded in the record.",
                            "deliverables": ["memo.docx"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return root

    def test_doctor_and_direct_command_work_outside_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.wrapper(directory)

            doctor = self.run_cli(directory, "adapter", "doctor", "legal", "--json")
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            report = json.loads(doctor.stdout)
            self.assertTrue(report["valid"])
            self.assertEqual(report["descriptor"]["name"], "legal")

            status = self.run_cli(
                directory,
                "legal",
                "status",
                "--repository",
                str(ROOT),
                "--json",
            )
            self.assertEqual(status.returncode, 0, status.stderr)
            result = json.loads(status.stdout)
            self.assertFalse(result["lab"]["profile_input"])
            self.assertFalse(result["syllogym"]["candidate_training_outcomes_used_by_adapter"])

            regressions = self.run_cli(
                directory,
                "legal",
                "regressions",
                "--repository",
                str(ROOT),
                "--json",
            )
            self.assertEqual(regressions.returncode, 0, regressions.stderr)
            regression_report = json.loads(regressions.stdout)
            self.assertEqual(regression_report["status"], "released_reproduced")
            self.assertFalse(regression_report["profile_input"])
            self.assertEqual(regression_report["support"]["severe_regressions"], 27)

            lab_root = self.make_lab(directory / "harvey-lab")
            initialized = self.run_cli(
                directory,
                "init",
                str(lab_root),
                "--adapter",
                "legal",
                "--revision",
                "git:fixture-revision",
                "--license",
                "MIT",
                "--json",
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            inspected = self.run_cli(directory, "inspect", str(lab_root), "--json")
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            inspection = json.loads(inspected.stdout)
            self.assertTrue(inspection["qualification_ready"])
            self.assertFalse(inspection["probe_ready"])
            qualified = self.run_cli(directory, "qualify", str(lab_root), "--json")
            self.assertEqual(qualified.returncode, 0, qualified.stderr)
            qualification = json.loads(qualified.stdout)
            self.assertEqual(qualification["status"], "qualified")
            self.assertFalse(qualification["model_responses_read"])
            self.assertFalse(qualification["outcomes_read"])

            intake = self.run_cli(
                directory,
                "legal",
                "lab-intake",
                "--repository",
                str(ROOT),
                "--lab-root",
                str(lab_root),
                "--source-revision",
                "fixture-revision",
                "--output-dir",
                str(directory / "intake"),
                "--json",
            )
            self.assertEqual(intake.returncode, 0, intake.stderr)
            intake_report = json.loads(intake.stdout)
            self.assertEqual(intake_report["task_count"], 1)
            self.assertFalse(intake_report["profile_input"])
            self.assertFalse(intake_report["outcomes_artifact_read"])
            first_summary = json.loads(
                (directory / "intake/lab-workflow-summary.json").read_text(encoding="utf-8")
            )
            first_digest = first_summary["source"]["task_set_sha256"]
            (lab_root / "tasks/litigation/draft-case-memo/documents/record.txt").write_text(
                "changed fixture",
                encoding="utf-8",
            )
            second_intake = self.run_cli(
                directory,
                "legal",
                "lab-intake",
                "--repository",
                str(ROOT),
                "--lab-root",
                str(lab_root),
                "--source-revision",
                "fixture-revision",
                "--output-dir",
                str(directory / "intake-2"),
                "--json",
            )
            self.assertEqual(second_intake.returncode, 0, second_intake.stderr)
            second_summary = json.loads(
                (directory / "intake-2/lab-workflow-summary.json").read_text(encoding="utf-8")
            )
            self.assertNotEqual(first_digest, second_summary["source"]["task_set_sha256"])

            run_dir = directory / "lab-results/run-1"
            run_dir.mkdir(parents=True)
            (run_dir / "config.json").write_text(
                json.dumps(
                    {
                        "run_id": "run-1",
                        "model": "provider/model-a",
                        "task": "litigation/draft-case-memo",
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "metrics.json").write_text(
                json.dumps({"finished_cleanly": True, "finish_reason": "finish_tool"}),
                encoding="utf-8",
            )
            (run_dir / "scores.json").write_text(
                json.dumps(
                    {
                        "judge_model": "judge-a",
                        "n_passed": 1,
                        "n_criteria": 1,
                    }
                ),
                encoding="utf-8",
            )
            unfinished_dir = directory / "lab-results/run-2"
            unfinished_dir.mkdir(parents=True)
            (unfinished_dir / "config.json").write_text(
                json.dumps(
                    {
                        "run_id": "run-2",
                        "model": "provider/model-a",
                        "task": "litigation/draft-case-memo",
                    }
                ),
                encoding="utf-8",
            )
            (unfinished_dir / "metrics.json").write_text(
                json.dumps({"finish_reason": "finish_tool"}),
                encoding="utf-8",
            )
            (unfinished_dir / "scores.json").write_text(
                json.dumps({"judge_model": "judge-a", "n_passed": 1, "n_criteria": 1}),
                encoding="utf-8",
            )
            malformed_score_dir = directory / "lab-results/run-3"
            malformed_score_dir.mkdir(parents=True)
            (malformed_score_dir / "config.json").write_text(
                json.dumps(
                    {
                        "run_id": "run-3",
                        "model": "provider/model-a",
                        "task": "litigation/draft-case-memo",
                    }
                ),
                encoding="utf-8",
            )
            (malformed_score_dir / "metrics.json").write_text(
                json.dumps({"finished_cleanly": True, "finish_reason": "finish_tool"}),
                encoding="utf-8",
            )
            (malformed_score_dir / "scores_dual.json").write_text(
                json.dumps(
                    {
                        "judges": ["judge-a", "judge-a"],
                        "dual_criterion_pass": 1.0,
                        "dual_all_pass_rate": 1.0,
                        "all_pass": "false",
                    }
                ),
                encoding="utf-8",
            )
            run_audit = self.run_cli(
                directory,
                "legal",
                "lab-runs",
                "--repository",
                str(ROOT),
                "--results-root",
                str(directory / "lab-results"),
                "--output-dir",
                str(directory / "run-audit"),
                "--json",
            )
            self.assertEqual(run_audit.returncode, 0, run_audit.stderr)
            run_report = json.loads(run_audit.stdout)
            self.assertEqual(run_report["support"]["valid_scored_runs"], 1)
            self.assertEqual(run_report["support"]["infrastructure_invalid_runs"], 2)
            rows = [
                json.loads(line)
                for line in (directory / "run-audit/lab-run-audit-rows.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            by_id = {row["run_id"]: row for row in rows}
            self.assertIn(
                "run_not_finished_cleanly",
                by_id["run-2"]["infrastructure_invalid_reasons"],
            )
            self.assertIn(
                "invalid_judge_score",
                by_id["run-3"]["infrastructure_invalid_reasons"],
            )


if __name__ == "__main__":
    unittest.main()
