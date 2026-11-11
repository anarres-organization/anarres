import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from anarres.finance import business_bench_source as business_bench
from anarres.finance import cli
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]


class FinanceCliTest(unittest.TestCase):
    def business_bench_fixture(self, root: Path) -> None:
        for index in range(business_bench.EXPECTED_DESK_TASKS):
            task = root / "tasks" / "desk" / f"desk-{index:03d}" / "task.yaml"
            task.parent.mkdir(parents=True)
            category = (
                "bookkeeping" if index < business_bench.EXPECTED_BOOKKEEPING_TASKS else "other"
            )
            task.write_text(f"category: {category}\n", encoding="utf-8")
        process_ids = sorted(business_bench.EXPECTED_WORKFLOWS) + [
            "process-extra-1",
            "process-extra-2",
            "process-extra-3",
            "process-extra-4",
            "process-extra-5",
        ]
        for process_id in process_ids:
            task_root = root / "tasks" / "process" / process_id
            task_root.mkdir(parents=True)
            for asset in business_bench.REQUIRED_PROCESS_ASSETS:
                path = task_root / asset
                content = f"id: {process_id}\n" if asset == "task.yaml" else "# fixture\n"
                path.write_text(content, encoding="utf-8")
        for relative in business_bench.REQUIRED_RUNTIME_PATHS:
            path = root / relative
            if Path(relative).suffix:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# fixture\n", encoding="utf-8")
            else:
                path.mkdir(parents=True, exist_ok=True)

    def source_manifest(
        self,
        root: Path,
        *,
        license_id: str = "MIT",
        adapter_version: str = "0.2.0",
        native_format: str = "business-bench-process-v1",
        revision: str | None = None,
    ) -> Path:
        manifest = root / "anarres.toml"
        source_revision = revision or f"git:{business_bench.EXPECTED_REVISION}"
        manifest.write_text(
            "\n".join(
                [
                    'schema_version = "anarres.environment-source.v1"',
                    'environment_id = "business-bench-process"',
                    'domain = "agentic-finance"',
                    'adapter = "finance"',
                    f'adapter_version = "{adapter_version}"',
                    f'native_format = "{native_format}"',
                    "",
                    "[source]",
                    'uri = "."',
                    f'revision = "{source_revision}"',
                    f'license = "{license_id}"',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return manifest

    def test_adapter_descriptor_is_stable_and_side_effect_free(self) -> None:
        descriptor = cli.adapter_descriptor()
        schema = json.loads(
            (ROOT / "schemas/adapters/adapter-descriptor.v1.schema.json").read_text()
        )
        Draft202012Validator(schema).validate(descriptor)
        self.assertEqual(descriptor["schema_version"], "anarres.adapter-descriptor.v1")
        self.assertEqual(descriptor["name"], "finance")
        self.assertEqual(descriptor["version"], "0.2.0")
        self.assertEqual(descriptor["protocol_version"], 2)
        self.assertEqual(descriptor["executable"], "anarres-finance")
        self.assertEqual(descriptor["capabilities"], sorted(set(descriptor["capabilities"])))
        self.assertEqual(
            descriptor["measurement_contracts"],
            ["finance.business-bench-starting-policy-qualification.v1"],
        )
        self.assertEqual(descriptor["source_formats"], ["business-bench-process-v1"])

    def test_native_source_qualification_preserves_the_outcome_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.business_bench_fixture(root)
            manifest = self.source_manifest(root)
            with (
                mock.patch.object(
                    business_bench,
                    "checkout_revision",
                    return_value=business_bench.EXPECTED_REVISION,
                ),
                mock.patch.object(
                    business_bench,
                    "checkout_has_tracked_changes",
                    return_value=False,
                ),
            ):
                result = cli.command_qualify_source(type("Args", (), {"manifest": manifest})())
        self.assertEqual(result["status"], "qualified")
        self.assertEqual(result["desk_task_families"], 187)
        self.assertEqual(result["bookkeeping_desk_task_families"], 36)
        self.assertEqual(result["process_task_families"], 9)
        self.assertEqual(len(result["qualified_workflows"]), 4)
        self.assertTrue(result["process_runtime_complete"])
        self.assertTrue(result["process_task_assets_complete"])
        self.assertFalse(result["policy_probe_available"])
        self.assertFalse(result["model_called"])
        self.assertFalse(result["scientific_outcomes_opened"])

    def test_native_source_qualification_rejects_wrong_license_and_incomplete_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.business_bench_fixture(root)
            wrong_license = self.source_manifest(root, license_id="unknown")
            with self.assertRaisesRegex(cli.FinanceCliError, "recorded as MIT"):
                cli.command_qualify_source(type("Args", (), {"manifest": wrong_license})())

            self.source_manifest(root)
            (root / "bench" / "process_run.py").unlink()
            with (
                mock.patch.object(
                    business_bench,
                    "checkout_revision",
                    return_value=business_bench.EXPECTED_REVISION,
                ),
                mock.patch.object(
                    business_bench,
                    "checkout_has_tracked_changes",
                    return_value=False,
                ),
                self.assertRaisesRegex(
                    business_bench.BusinessBenchSourceError,
                    "process runtime is incomplete",
                ),
            ):
                cli.command_qualify_source(type("Args", (), {"manifest": root / "anarres.toml"})())

    def test_native_source_qualification_rejects_wrong_version_format_and_revision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.business_bench_fixture(root)
            for manifest_options, message in (
                ({"adapter_version": "0.1.0"}, "installed adapter"),
                ({"native_format": "unknown-v1"}, "format"),
                ({"revision": "git:deadbeef"}, "pinned"),
            ):
                manifest = self.source_manifest(root, **manifest_options)
                with self.assertRaisesRegex(ValueError, message):
                    cli.command_qualify_source(type("Args", (), {"manifest": manifest})())

    def test_native_source_qualification_rejects_modified_tracked_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.business_bench_fixture(root)
            manifest = self.source_manifest(root)
            with (
                mock.patch.object(
                    business_bench,
                    "checkout_revision",
                    return_value=business_bench.EXPECTED_REVISION,
                ),
                mock.patch.object(
                    business_bench,
                    "checkout_has_tracked_changes",
                    return_value=True,
                ),
                self.assertRaisesRegex(
                    business_bench.BusinessBenchSourceError,
                    "differ from the pinned revision",
                ),
            ):
                cli.command_qualify_source(type("Args", (), {"manifest": manifest})())

    def test_status_reports_released_capabilities(self) -> None:
        result = cli.command_status(type("Args", (), {"repository": ROOT})())
        self.assertEqual(result["domain"], "agentic-finance")
        self.assertIn("retrospective_reproduction", result["capabilities"])
        self.assertIn("native_source_qualification", result["capabilities"])
        self.assertEqual(result["native_source_format"], "business-bench-process-v1")
        self.assertFalse(result["native_policy_probe_available"])
        self.assertIn("portable execution contract", result["native_policy_probe_boundary"])
        self.assertFalse(result["prospective_environment_outcome_opened"])
        self.assertGreaterEqual(result["strict_retrospective_sources"], 1)
        self.assertEqual(result["strict_pairwise_ordering"], 0.815534)
        self.assertEqual(result["strict_source_macro_pairwise_ordering"], 0.836357)
        self.assertEqual(result["selective_pairwise_accuracy"], 0.904255)
        self.assertEqual(result["selective_source_macro_accuracy"], 0.895817)
        self.assertEqual(result["selective_pairwise_coverage"], 0.760518)
        self.assertEqual(result["selective_decided_pairs"], 235)
        self.assertEqual(result["candidate_decision_threshold"], 0.2)
        self.assertEqual(result["candidate_decision_retrospective_accuracy"], 0.903433)
        self.assertEqual(result["candidate_decision_retrospective_coverage"], 0.754045)
        self.assertEqual(result["regression_risk_contrasts"], 165)
        self.assertEqual(result["regression_risk_source_macro_roc_auc"], 0.815183)
        self.assertEqual(result["regression_risk_eligible_sources"], 5)
        self.assertEqual(result["excluded_source_finacumen_pairwise_correct"], 33)
        self.assertEqual(result["excluded_source_finacumen_pairwise_scored"], 33)
        self.assertEqual(result["excluded_source_finacumen_pairwise_abstained"], 4)
        self.assertEqual(result["excluded_source_fintoolsyn_directional_correct"], 9)
        self.assertEqual(result["excluded_source_fintoolsyn_directional_scored"], 9)
        self.assertEqual(result["excluded_source_fintoolsyn_regression_correct"], 3)
        self.assertEqual(result["excluded_source_fintoolsyn_regression_scored"], 3)
        self.assertEqual(result["outcome_separated_longfinanceqa_directional_correct"], 24)
        self.assertEqual(result["outcome_separated_longfinanceqa_directional_scored"], 25)
        self.assertEqual(result["outcome_separated_longfinanceqa_families_supported"], 4)
        self.assertEqual(result["outcome_separated_longfinanceqa_families_scored"], 4)

    def test_source_audit_uses_native_implementation(self) -> None:
        result = cli.command_audit_sources(type("Args", (), {"repository": ROOT})())
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["generator_trials_passed"], 20)
        self.assertFalse(result["scientific_outcomes_opened"])

    def test_candidate_decision_selects_or_abstains_and_reports_regression(self) -> None:
        weights = json.loads(
            (
                ROOT
                / "experiments/finance/retrospective-post-training/results/expanded_summary.json"
            ).read_text()
        )["practical_rule_weights"]
        zero = {name: 0.0 for name in weights}
        aligned = {**zero, "target_alignment": 1.0}
        nearby = {**zero, "target_alignment": 0.9}
        panel = {
            "schema_version": "anarres.finance-candidate-panel.v1",
            "target_id": "test-target",
            "baseline_id": "base",
            "candidates": [
                {"candidate_id": "base", "features": zero},
                {"candidate_id": "aligned", "features": aligned},
                {"candidate_id": "nearby", "features": nearby},
            ],
        }
        schema = json.loads((ROOT / "schemas/finance-candidate-panel.v1.schema.json").read_text())
        Draft202012Validator(schema).validate(panel)
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "panel.json"
            input_path.write_text(json.dumps(panel), encoding="utf-8")
            args = type(
                "Args",
                (),
                {"repository": ROOT, "input": input_path, "output": None, "force": False},
            )()
            result = cli.command_decide(args)

        self.assertEqual(result["decision"], "abstain")
        self.assertEqual(result["candidate_set"], ["aligned", "nearby"])
        self.assertEqual(result["threshold"], 0.2)
        directions = {
            row["candidate_id"]: row["direction"] for row in result["regression_directions"]
        }
        self.assertEqual(directions, {"aligned": "improve", "nearby": "improve"})
        self.assertEqual(result["evidence"]["pairwise_accuracy"], 0.903433)

    def test_candidate_decision_rejects_fields_outside_the_schema(self) -> None:
        weights = json.loads(
            (
                ROOT
                / "experiments/finance/retrospective-post-training/results/expanded_summary.json"
            ).read_text()
        )["practical_rule_weights"]
        features = {name: 0.0 for name in weights}
        panel = {
            "schema_version": "anarres.finance-candidate-panel.v1",
            "target_id": "test-target",
            "unexpected": True,
            "candidates": [
                {"candidate_id": "first", "features": features},
                {"candidate_id": "second", "features": features},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "panel.json"
            input_path.write_text(json.dumps(panel), encoding="utf-8")
            args = type(
                "Args",
                (),
                {"repository": ROOT, "input": input_path, "output": None, "force": False},
            )()
            with self.assertRaisesRegex(cli.FinanceCliError, "unsupported fields"):
                cli.command_decide(args)

    def test_profile_command_exports_native_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = type(
                "Args",
                (),
                {
                    "repository": ROOT,
                    "result": None,
                    "protocol": None,
                    "preflight": None,
                    "sources": None,
                    "harness": None,
                    "output_dir": Path(directory),
                    "force": False,
                },
            )()
            result = cli.command_profile(args)
            profile = json.loads(Path(result["output"]).read_text())
        self.assertEqual(result["status"], "exported")
        self.assertFalse(result["qualified"])
        self.assertEqual(profile["domain"], "agentic-finance")

    def test_frozen_holdout_can_be_rescored(self) -> None:
        args = type("Args", (), {"repository": ROOT, "name": "finharmbench"})()
        result = cli.command_score_holdout(args)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["holdout"], "heldout-finharmbench")
        self.assertEqual(
            result["score"]["accepted_models"],
            [
                "llama3_8b_instruct",
                "adaptllm_finance_chat_7b",
            ],
        )

    def test_compact_verify_checks_released_finance_evidence(self) -> None:
        args = type("Args", (), {"repository": ROOT, "exhaustive": False})()
        result = cli.command_verify(args)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["mode"], "compact")
        self.assertEqual(result["manifest_artifacts"], 38)
        self.assertEqual(result["retrospective_sources"], 16)
        self.assertEqual(result["strict_panels"], 79)
        self.assertEqual(result["selective_pairwise_accuracy"], 0.904255)
        self.assertEqual(result["selective_pairwise_coverage"], 0.760518)
        self.assertEqual(result["regression_risk_source_macro_roc_auc"], 0.815183)
        self.assertEqual(result["fintoolsyn_directional_correct"], 9)
        self.assertEqual(result["fintoolsyn_directional_scored"], 9)
        self.assertEqual(result["fintoolsyn_regression_correct"], 3)
        self.assertEqual(result["fintoolsyn_regression_scored"], 3)
        self.assertEqual(result["longfinanceqa_directional_correct"], 24)
        self.assertEqual(result["longfinanceqa_directional_scored"], 25)
        self.assertEqual(result["longfinanceqa_families_supported"], 4)
        self.assertEqual(result["longfinanceqa_families_scored"], 4)
        self.assertFalse(result["starting_policy_qualified"])
        self.assertEqual(len(result["holdouts"]), 7)

    def test_manifest_verification_rejects_changed_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "artifact.json"
            artifact.write_text("{}\n", encoding="utf-8")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"artifact.json": "0" * 64}) + "\n", encoding="utf-8")
            with self.assertRaises(cli.FinanceCliError):
                cli.verify_manifest(root, manifest)

    def test_zero_signal_record_preserves_cost_and_fails_readiness(self) -> None:
        rows = []
        for scenario in range(2):
            for rollout in range(4):
                rows.append(
                    {
                        "policy_id": "zero-signal-policy",
                        "workflow": "reconciliation",
                        "scenario_id": f"scenario-{scenario}",
                        "rollout_seed": rollout,
                        "infrastructure_valid": True,
                        "tool_protocol_valid": True,
                        "reward": 0,
                        "material_control_violation": False,
                        "generated_tokens": 500 + rollout,
                        "tool_calls": 2,
                        "truncated": False,
                    }
                )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "attempts.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows))
            args = type(
                "Args",
                (),
                {
                    "repository": ROOT,
                    "input": path,
                    "expected_workflows": 1,
                    "expected_scenarios_per_workflow": 2,
                    "group_size": 4,
                    "output": None,
                    "force": False,
                },
            )()
            result = cli.command_qualify_policy(args)
        self.assertEqual(result["completion_rate"], 0.0)
        self.assertEqual(result["mixed_group_fraction"], 0.0)
        self.assertGreater(result["median_generated_tokens"], 0)
        self.assertFalse(result["qualified"])
        self.assertFalse(result["gates"]["completion_rate_between_0_02_and_0_80"])
        self.assertFalse(result["gates"]["mixed_group_fraction_at_least_0_10"])

    def test_reproduction_refuses_existing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            report = {"status": "pass", "test_count": 1, "artifacts": {}}
            cli.write_json(output / "REPRODUCTION.json", report)
            with self.assertRaises(FileExistsError):
                cli.copy_reproduced_artifacts(output, output, report, force=False)


if __name__ == "__main__":
    unittest.main()
