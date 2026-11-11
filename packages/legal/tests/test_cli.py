import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from anarres.legal import cli

ROOT = Path(__file__).resolve().parents[3]


class LegalCliTest(unittest.TestCase):
    def digest(self, label: str) -> str:
        return f"sha256:{hashlib.sha256(label.encode()).hexdigest()}"

    def make_execution_contract(self) -> dict[str, object]:
        return {
            "schema_version": "anarres.legal-lab-execution-contract.v1",
            "contract_id": "lab-starting-policy-fixture-v1",
            "source": {
                "environment_id": "lab-fixture",
                "revision": "git:fixture-revision",
                "task_set_sha256": self.digest("task-set"),
                "license": "MIT",
            },
            "starting_policy_stage": {
                "policy": {
                    "model_id": "provider/frontier-legal-model",
                    "model_revision": "provider-snapshot-1",
                    "checkpoint_id": "warm-start",
                    "checkpoint_revision": "checkpoint-1",
                },
                "harness": {
                    "name": "lab-core",
                    "version": "1.3.0",
                    "revision": "git:fixture-harness",
                    "package_sha256": self.digest("lab-core-wheel"),
                },
                "system_prompt_sha256": self.digest("system-prompt"),
                "skills": [],
                "allowed_tools": ["bash", "read", "write", "edit", "glob", "grep", "finish"],
                "document_access": {
                    "matter_documents": "read_only",
                    "output": "write_only_inside_output",
                    "network": "disabled",
                },
                "sandbox_image": "lab-sandbox:fixture",
                "sandbox_image_digest": self.digest("sandbox-image"),
                "max_turns": 40,
                "temperature": 0,
                "reasoning_effort": "high",
                "shell_timeout_seconds": 60,
                "finish_tool_enabled": True,
                "compaction": {
                    "strategy": "none",
                    "implementation_revision": None,
                    "context_window_tokens": None,
                    "trigger_tokens": None,
                },
            },
            "judge_stage": {
                "harness": {
                    "name": "lab-core",
                    "version": "1.3.0",
                    "revision": "git:fixture-harness",
                    "package_sha256": self.digest("lab-core-wheel"),
                },
                "judge_profile": "lab-standard-dual-v1",
                "judges": [
                    {"model_id": "judge-a", "model_revision": "judge-a-snapshot"},
                    {"model_id": "judge-b", "model_revision": "judge-b-snapshot"},
                ],
                "rubric_prompt_sha256": self.digest("rubric-prompt"),
                "grader_revision": "git:fixture-grader",
                "document_conversion": {
                    "pandoc_version": "3.5",
                    "track_changes_mode": "all",
                },
                "parallel_calls": 6,
                "retry": {
                    "max_attempts": 6,
                    "backoff_seconds": 20,
                    "retryable_conditions": ["rate_limit", "server_error", "overload"],
                },
            },
            "outcome_semantics": {
                "criterion": "binary_pass_fail",
                "all_pass": "every_criterion_passes_for_each_judge",
                "headline": "task_all_pass",
                "deliverable_completion": {
                    "metric": "required_deliverables_present",
                    "missing_required_deliverable": "scientific_failure_when_execution_valid",
                },
            },
            "accounting": {
                "metrics": [
                    "agent_input_tokens",
                    "agent_output_tokens",
                    "agent_wall_clock_seconds",
                    "judge_calls",
                    "judge_input_tokens",
                    "judge_output_tokens",
                    "judge_wall_clock_seconds",
                    "retry_count",
                    "estimated_cost",
                ],
                "currency": "USD",
                "price_schedule_revision": "fixture-pricing-1",
                "retry_accounting": "record_all_attempts",
            },
            "infrastructure_invalid_conditions": [
                "contract_mismatch",
                "document_conversion_failure",
                "judge_outage",
                "missing_judge_score",
                "missing_metrics",
                "model_outage",
                "run_not_finished_cleanly",
                "sandbox_failure",
                "ungraded_criterion",
            ],
            "target_scope": {
                "practice_areas": ["corporate-ma"],
                "workflows": ["corporate-ma/review-change-of-control"],
                "diagnostics": ["criterion_pass_rate", "document_coverage"],
                "protected_outcomes": {
                    "practice_areas": ["corporate-ma"],
                    "workflow_outcomes": ["task_all_pass"],
                    "available_before_freeze": False,
                },
            },
            "execution": {
                "mode": "contract_only",
                "execution_started": False,
                "submission_requires_explicit_command": True,
                "credentials": {"inherited_at_runtime": True, "serialized": False},
            },
        }

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

    def make_lab_results(self, root: Path) -> Path:
        valid = root / "valid"
        invalid = root / "invalid"
        valid.mkdir(parents=True)
        invalid.mkdir(parents=True)
        common = {
            "model": "provider/frontier-legal-model",
            "task": "corporate-ma/review-change-of-control",
            "max_turns": 40,
            "temperature": 0,
            "reasoning_effort": "high",
            "skills": ["documents"],
            "sandbox_image": "lab-sandbox@sha256:fixture",
            "enable_finish": True,
        }
        (valid / "config.json").write_text(
            json.dumps({**common, "run_id": "valid-run"}), encoding="utf-8"
        )
        (valid / "metrics.json").write_text(
            json.dumps(
                {
                    "finished_cleanly": True,
                    "finish_reason": "finish_tool",
                    "documents_read": 8,
                    "total_documents": 10,
                    "input_tokens": 1000,
                    "output_tokens": 200,
                    "wall_clock_seconds": 20,
                }
            ),
            encoding="utf-8",
        )
        (valid / "scores_dual.json").write_text(
            json.dumps(
                {
                    "judges": ["judge-a", "judge-b"],
                    "judge_profile": "custom-dual",
                    "dual_criterion_pass": 0.75,
                    "dual_all_pass_rate": 0.5,
                    "all_pass": False,
                }
            ),
            encoding="utf-8",
        )
        (invalid / "config.json").write_text(
            json.dumps({**common, "run_id": "invalid-run"}), encoding="utf-8"
        )
        (invalid / "metrics.json").write_text(
            json.dumps({"finished_cleanly": False, "finish_reason": "context_overflow"}),
            encoding="utf-8",
        )
        return root

    def test_descriptor_is_sorted_and_side_effect_free(self) -> None:
        descriptor = cli.adapter_descriptor()
        self.assertEqual(descriptor["schema_version"], "anarres.adapter-descriptor.v1")
        self.assertEqual(descriptor["name"], "legal")
        self.assertEqual(descriptor["executable"], "anarres-legal")
        self.assertEqual(descriptor["capabilities"], sorted(set(descriptor["capabilities"])))
        self.assertEqual(descriptor["version"], "0.4.0")
        self.assertIn("lab-execution-contract", descriptor["capabilities"])
        self.assertEqual(descriptor["source_formats"], ["harvey-lab-checkout-v1"])
        self.assertIn("source-qualification", descriptor["capabilities"])
        self.assertNotIn("policy-probe", descriptor["capabilities"])

    def write_source_manifest(self, root: Path, lab_root: Path, *, license_id: str = "MIT") -> Path:
        manifest = root / "anarres.toml"
        manifest.write_text(
            "\n".join(
                [
                    'schema_version = "anarres.environment-source.v1"',
                    'environment_id = "lab-fixture"',
                    'domain = "legal-procedural-reasoning"',
                    'adapter = "legal"',
                    'adapter_version = "0.4.0"',
                    'native_format = "harvey-lab-checkout-v1"',
                    "",
                    "[source]",
                    f'uri = "{lab_root.as_posix()}"',
                    'revision = "git:fixture-revision"',
                    f'license = "{license_id}"',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return manifest

    def test_native_lab_source_qualification_is_outcome_blind(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lab_root = self.make_lab(root / "lab")
            manifest = self.write_source_manifest(root, lab_root)
            result = cli.command_qualify_source(type("Args", (), {"manifest": manifest})())
        self.assertEqual(result["status"], "qualified")
        self.assertEqual(result["tasks"], 1)
        self.assertEqual(result["practice_areas"], 1)
        self.assertFalse(result["policy_probe_available"])
        self.assertFalse(result["model_responses_read"])
        self.assertFalse(result["outcomes_read"])

    def test_native_lab_source_rejects_wrong_license_and_missing_documents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lab_root = self.make_lab(root / "lab")
            wrong_license = self.write_source_manifest(root, lab_root, license_id="unknown")
            with self.assertRaisesRegex(cli.LegalCliError, "must be recorded as MIT"):
                cli.command_qualify_source(type("Args", (), {"manifest": wrong_license})())

            wrong_license.unlink()
            for document in (lab_root / "tasks").rglob("documents/*"):
                document.unlink()
            incomplete = self.write_source_manifest(root, lab_root)
            with self.assertRaisesRegex(cli.LegalCliError, "incomplete matter files"):
                cli.command_qualify_source(type("Args", (), {"manifest": incomplete})())

    def test_status_separates_syllogym_from_lab(self) -> None:
        args = type("Args", (), {"repository": ROOT})()
        result = cli.command_status(args)
        self.assertFalse(result["syllogym"]["candidate_training_outcomes_used_by_adapter"])
        self.assertEqual(result["lab"]["role"], "separate_task_regression_evaluation")
        self.assertFalse(result["lab"]["profile_input"])
        self.assertTrue(result["lab"]["workflow_intake_available"])
        self.assertFalse(result["lab"]["workflow_intake_reads_outcomes"])
        self.assertTrue(result["lab"]["execution_contract_available"])
        self.assertFalse(result["lab"]["execution_contract_starts_execution"])

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

    def test_lab_run_audit_preserves_invalid_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results = self.make_lab_results(root / "results")
            output = root / "audit"
            args = type(
                "Args",
                (),
                {
                    "repository": ROOT,
                    "results_root": results,
                    "run_manifest": None,
                    "output_dir": output,
                    "force": False,
                },
            )()
            result = cli.command_lab_runs(args)
            rows = [
                json.loads(line)
                for line in (output / "lab-run-audit-rows.jsonl").read_text().splitlines()
            ]
        self.assertEqual(result["status"], "complete_with_invalid_runs")
        self.assertEqual(result["support"]["valid_scored_runs"], 1)
        self.assertEqual(result["support"]["infrastructure_invalid_runs"], 1)
        invalid = next(row for row in rows if row["run_id"] == "invalid-run")
        self.assertFalse(invalid["valid_scored_run"])
        self.assertIsNone(invalid["criterion_pass_rate"])
        self.assertIn("run_not_finished_cleanly", invalid["infrastructure_invalid_reasons"])
        self.assertIn("missing_judge_score", invalid["infrastructure_invalid_reasons"])

    def test_lab_execution_contract_is_strict_and_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            draft = root / "draft.json"
            output = root / "contract.json"
            draft.write_text(json.dumps(self.make_execution_contract()), encoding="utf-8")
            args = type(
                "Args",
                (),
                {"input": draft, "output": output, "force": False},
            )()
            first = cli.command_lab_contract(args)
            first_bytes = output.read_bytes()
            output.unlink()
            second = cli.command_lab_contract(args)
            second_bytes = output.read_bytes()
            contract = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(first, second)
        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(first["status"], "qualified")
        self.assertFalse(first["execution_started"])
        self.assertFalse(first["policy_probe_available"])
        self.assertEqual(contract["contract_sha256"], first["contract_sha256"])

    def test_lab_execution_contract_rejects_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            draft = self.make_execution_contract()
            draft["starting_policy_stage"]["api_key"] = "do-not-store-this"
            path = Path(directory) / "draft.json"
            path.write_text(json.dumps(draft), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "credential material"):
                cli.lab_execution.load(path)

    def test_lab_run_audit_detects_judge_and_compaction_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results = self.make_lab_results(root / "results")
            contract_path = root / "contract.json"
            contract_path.write_text(json.dumps(self.make_execution_contract()), encoding="utf-8")
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "runs": [
                            {
                                "run_id": run_id,
                                "contract_id": "lab-starting-policy-fixture-v1",
                                "model_revision": "provider-snapshot-1",
                                "checkpoint_id": "warm-start",
                                "checkpoint_revision": "checkpoint-1",
                            }
                            for run_id in ("valid-run", "invalid-run")
                        ]
                    }
                ),
                encoding="utf-8",
            )
            valid_config_path = results / "valid/config.json"
            valid_config = json.loads(valid_config_path.read_text(encoding="utf-8"))
            valid_config.update(
                {
                    "shell_timeout": 60,
                    "compaction": {"strategy": "rolling-summary"},
                }
            )
            valid_config_path.write_text(json.dumps(valid_config), encoding="utf-8")
            output = root / "audit"
            result = cli.command_lab_runs(
                type(
                    "Args",
                    (),
                    {
                        "repository": ROOT,
                        "results_root": results,
                        "run_manifest": manifest_path,
                        "execution_contract": contract_path,
                        "output_dir": output,
                        "force": False,
                    },
                )()
            )
            rows = [
                json.loads(line)
                for line in (output / "lab-run-audit-rows.jsonl").read_text().splitlines()
            ]
        row = next(item for item in rows if item["run_id"] == "valid-run")
        self.assertEqual(result["status"], "complete_with_invalid_runs")
        self.assertIn("compaction_contract_mismatch", row["infrastructure_invalid_reasons"])
        self.assertIn("judge_contract_mismatch", row["infrastructure_invalid_reasons"])

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
