import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "experiments/robotics/environment-selection/prospective-cupid-can-v141"
SCRIPT = STUDY / "export_environment_profiles.py"
SPEC = importlib.util.spec_from_file_location("robotics_cupid_profile_adapter", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
CLI_PATH = STUDY / "src/anarres_robotics_adapter/cli.py"
CLI_SPEC = importlib.util.spec_from_file_location("anarres_robotics_cli", CLI_PATH)
assert CLI_SPEC is not None and CLI_SPEC.loader is not None
CLI = importlib.util.module_from_spec(CLI_SPEC)
CLI_SPEC.loader.exec_module(CLI)


class RoboticsCupidProfileAdapterTest(unittest.TestCase):
    def test_protocol_freeze_lineage_validates(self) -> None:
        result = subprocess.run(
            [sys.executable, str(STUDY / "scripts/validate_protocol.py")],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        freeze = json.loads(result.stdout)
        correction = json.loads((STUDY / "FREEZE_CORRECTION.json").read_text())
        self.assertEqual(freeze, correction["corrected_freeze"])

    def test_adapter_descriptor_matches_the_shared_contract(self) -> None:
        descriptor = CLI.adapter_descriptor()
        schema = json.loads(
            (ROOT / "schemas/adapters/adapter-descriptor.v1.schema.json").read_text()
        )
        Draft202012Validator(schema).validate(descriptor)
        self.assertEqual(descriptor["name"], "robotics")
        self.assertEqual(descriptor["version"], "0.3.0")
        self.assertEqual(descriptor["executable"], "anarres-robotics")
        self.assertEqual(descriptor["capabilities"], sorted(set(descriptor["capabilities"])))
        self.assertEqual(
            descriptor["measurement_contracts"],
            ["robotics.cupid-can-v141-candidate-measurement.v1"],
        )

    def run_adapter(self, arguments: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        source_paths = [
            STUDY / "src",
            ROOT / "packages/core/src",
            ROOT / "packages/environments/src",
        ]
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(str(path) for path in source_paths)
        return subprocess.run(
            [sys.executable, "-m", "anarres_robotics_adapter.cli", *arguments],
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_adapter_runs_outside_the_repository_with_an_explicit_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory)
            descriptor = self.run_adapter(["--anarres-adapter-descriptor"], outside)
            self.assertEqual(descriptor.returncode, 0, descriptor.stderr)
            self.assertEqual(json.loads(descriptor.stdout)["name"], "robotics")

            status = self.run_adapter(["status", "--repository", str(ROOT), "--json"], outside)
            self.assertEqual(status.returncode, 0, status.stderr)
            report = json.loads(status.stdout)
            self.assertTrue(report["qualification_passed"])
            self.assertTrue(report["measurement_reliability_passed"])
            self.assertFalse(report["candidate_outcomes_opened"])
            self.assertFalse(report["selector_performance_validated"])
            self.assertEqual(report["candidate_count"], 5)
            self.assertIn("operator_tier_effective_coverage", report["profile_coordinates"])
            self.assertIn("starting_policy_failure_rate", report["profile_context"])

            plan_path = outside / "can-v141.plan.json"
            planned = self.run_adapter(
                [
                    "plan",
                    "--repository",
                    str(ROOT),
                    "--output",
                    str(plan_path),
                    "--json",
                ],
                outside,
            )
            self.assertEqual(planned.returncode, 0, planned.stderr)
            plan_report = json.loads(planned.stdout)
            self.assertFalse(plan_report["execution_started"])
            self.assertFalse(plan_report["submission_ready"])
            self.assertFalse(plan_report["candidate_outcomes_opened"])
            self.assertEqual(plan_report["candidate_runs"], 25)

            plan = json.loads(plan_path.read_text())
            schema = json.loads(
                (ROOT / "schemas/workflows/robotics-workflow-plan.v1.schema.json").read_text()
            )
            Draft202012Validator(schema).validate(plan)
            recorded_digest = plan.pop("plan_digest")
            self.assertEqual(recorded_digest, CLI.sha256_object(plan))
            self.assertEqual(plan["totals"]["candidate_arms"], 5)
            self.assertEqual(plan["totals"]["candidate_runs"], 25)
            self.assertEqual(plan["totals"]["optimizer_steps"], 1_250_000)
            self.assertEqual(plan["totals"]["evaluation_episodes"], 2_500)
            self.assertEqual(len(plan["candidate_runs"]), 25)
            self.assertFalse(plan["execution"]["submission_ready"])
            self.assertIsNone(plan["execution"]["scheduler"])
            self.assertEqual(
                [stage["stage_id"] for stage in plan["stages"]],
                ["preflight", "train", "evaluate", "release_gate", "score"],
            )
            self.assertFalse(plan["stages"][-2]["opens_candidate_outcomes"])
            self.assertTrue(plan["stages"][-1]["opens_candidate_outcomes"])
            self.assertFalse(plan["scientific_boundary"]["candidate_outcomes_opened"])

            repeated_plan = outside / "can-v141-repeated.plan.json"
            repeated = self.run_adapter(
                [
                    "plan",
                    "--repository",
                    str(ROOT),
                    "--output",
                    str(repeated_plan),
                    "--json",
                ],
                outside,
            )
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            self.assertEqual(plan_path.read_bytes(), repeated_plan.read_bytes())

            refused = self.run_adapter(
                [
                    "plan",
                    "--repository",
                    str(ROOT),
                    "--output",
                    str(plan_path),
                    "--json",
                ],
                outside,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("already exists", refused.stderr)

            output = outside / "profiles"
            profiled = self.run_adapter(
                [
                    "profile",
                    "--repository",
                    str(ROOT),
                    "--output-dir",
                    str(output),
                    "--json",
                ],
                outside,
            )
            self.assertEqual(profiled.returncode, 0, profiled.stderr)
            profile_report = json.loads(profiled.stdout)
            self.assertEqual(profile_report["profile_count"], 5)
            self.assertFalse(profile_report["candidate_outcomes_opened"])

            verified = self.run_adapter(["verify", "--repository", str(ROOT), "--json"], outside)
            self.assertEqual(verified.returncode, 0, verified.stderr)
            verification = json.loads(verified.stdout)
            self.assertEqual(verification["status"], "pass")
            self.assertTrue(verification["deterministic_profiles"])
            self.assertTrue(verification["deterministic_plan"])
            self.assertEqual(verification["planned_candidate_runs"], 25)
            self.assertFalse(verification["submission_ready"])

            results = self.run_adapter(["results", "--repository", str(ROOT), "--json"], outside)
            self.assertEqual(results.returncode, 0, results.stderr)
            result = json.loads(results.stdout)
            self.assertFalse(result["profile_input"])
            self.assertTrue(result["candidate_outcomes_opened"])
            self.assertTrue(result["abstention_correct"])
            self.assertEqual(result["observed_best"], "diversity_only_retain_25")
            self.assertIn("not selector superiority", result["claim_boundary"])
            self.assertEqual(set(result["artifacts"]), {"outcomes", "reproducer", "summary"})
            self.assertTrue(
                all(value.startswith("sha256:") for value in result["artifacts"].values())
            )
            repeated = self.run_adapter(["results", "--repository", str(ROOT), "--json"], outside)
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            self.assertEqual(results.stdout, repeated.stdout)

    def export(
        self,
        output: Path,
        *,
        measurements: Path = MODULE.DEFAULT_MEASUREMENTS,
        sources: Path = MODULE.DEFAULT_SOURCES,
        qualification: Path = MODULE.DEFAULT_QUALIFICATION,
    ) -> list[Path]:
        return MODULE.export_profiles(
            measurements_path=measurements,
            protocol_path=MODULE.DEFAULT_PROTOCOL,
            sources_path=sources,
            qualification_path=qualification,
            output_dir=output,
        )

    def test_real_measurements_export_five_schema_valid_profiles(self) -> None:
        schema_paths = sorted((ROOT / "schemas").rglob("*.schema.json"))
        schemas = [json.loads(path.read_text()) for path in schema_paths]
        registry = Registry()
        for item in schemas:
            if isinstance(item.get("$id"), str):
                registry = registry.with_resource(item["$id"], Resource.from_contents(item))
        schema = next(
            item
            for item in schemas
            if item.get("$id", "").endswith("environment-profile-input.v1.schema.json")
        )
        with tempfile.TemporaryDirectory() as directory:
            outputs = self.export(Path(directory))
            self.assertEqual(len(outputs), 5)
            profiles = [json.loads(path.read_text()) for path in outputs]
            for profile in profiles:
                Draft202012Validator(schema, registry=registry).validate(profile)
                self.assertEqual(profile["domain"], "robotics")
                self.assertFalse(profile["attributes"]["candidate_outcomes_opened"])
                self.assertEqual(len(profile["coordinates"]), 4)
                attributes = profile["attributes"]
                self.assertEqual(attributes["score_missingness_rate"], 0.0)
                self.assertEqual(
                    attributes["score_missingness_rate_unit"], "fraction_of_expected_scores"
                )
                self.assertGreater(attributes["starting_policy_failure_rate"], 0.0)
                self.assertEqual(
                    attributes["starting_policy_failure_rate_unit"],
                    "fraction_of_scoring_rollouts",
                )
                self.assertIn(attributes["selected_fraction"], {0.5, 1.0})
                self.assertEqual(
                    attributes["selected_fraction_unit"], "fraction_of_demonstration_pool"
                )
                self.assertIsInstance(attributes["candidate_construction"], str)
                self.assertEqual(
                    attributes["better_tier_count"]
                    + attributes["okay_tier_count"]
                    + attributes["worse_tier_count"],
                    attributes["candidate_count"],
                )
                self.assertTrue(
                    all(check["status"] == "pass" for check in profile["qualification_checks"])
                )
            selected = [p for p in profiles if p["attributes"]["frozen_point_prediction"]]
            self.assertEqual(len(selected), 1)
            self.assertEqual(selected[0]["attributes"]["candidate_id"], "cupid_tier_balanced_50")
            self.assertTrue(selected[0]["attributes"]["tier_balance_constraint_applied"])

            coordinates = {item["name"]: item for item in selected[0]["coordinates"]}
            self.assertEqual(coordinates["mean_cupid_rank_percentile"]["unit"], "rank_percentile")
            self.assertEqual(coordinates["operator_tier_effective_coverage"]["unit"], "fraction")
            self.assertEqual(
                coordinates["mean_demonstration_action_steps"]["unit"],
                "action_steps_per_demonstration",
            )
            self.assertEqual(
                coordinates["measurement_rank_reliability"]["unit"],
                "spearman_correlation",
            )

    def test_native_artifact_digests_are_exact_and_output_is_deterministic(self) -> None:
        expected_measurement = hashlib.sha256(MODULE.DEFAULT_MEASUREMENTS.read_bytes()).hexdigest()
        native = json.loads(MODULE.DEFAULT_MEASUREMENTS.read_text())["native_inputs"]
        self.assertEqual(
            native["candidate_freeze_sha256"],
            "3b3b34e544dd5a1ce0740fb534a7fb0f5213f89173e657e6889b9e9e16ff5c8f",
        )
        self.assertEqual(
            set(native["score_sha256"].values()),
            {
                "cb7c905a9890f69bf0c450606dd0702b7fca563915f49fa34451901b0867d82f",
                "f790676cb101b6cb9f314c7d8cb819fbacb20ae1424ede22cae1592d21884795",
                "0d18a60f16edd8a033bf50c01b5d003dc018ae906c008b387606f54a69b8b33c",
            },
        )
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            outputs_a = self.export(Path(first))
            outputs_b = self.export(Path(second))
            self.assertEqual(
                [path.read_bytes() for path in outputs_a],
                [path.read_bytes() for path in outputs_b],
            )
            profile = json.loads(outputs_a[0].read_text())
            artifacts = {item["role"]: item["reference"] for item in profile["artifacts"]}
            self.assertEqual(
                artifacts["native-measurements"]["sha256"], f"sha256:{expected_measurement}"
            )

    def test_zero_and_negative_finite_measurements_are_not_clamped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            measurements = json.loads(MODULE.DEFAULT_MEASUREMENTS.read_text())
            candidate = measurements["candidates"]["all_data"]["coordinates"]
            candidate["mean_cupid_rank_percentile"] = -0.25
            candidate["operator_tier_effective_coverage"] = 0.0
            modified = temporary / "measurements.json"
            modified.write_text(json.dumps(measurements))
            outputs = self.export(temporary / "profiles", measurements=modified)
            profile = json.loads(outputs[0].read_text())
            values = {item["name"]: item["value"] for item in profile["coordinates"]}
            self.assertEqual(values["mean_cupid_rank_percentile"], -0.25)
            self.assertEqual(values["operator_tier_effective_coverage"], 0.0)

    def test_missing_source_revision_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            sources = json.loads(MODULE.DEFAULT_SOURCES.read_text())
            sources["sources"][-1].pop("revision")
            modified = temporary / "sources.json"
            modified.write_text(json.dumps(sources))
            with self.assertRaisesRegex(MODULE.AdapterError, "URI, revision, or license"):
                self.export(temporary / "profiles", sources=modified)

    def test_protocol_digest_and_sealed_outcomes_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            measurements = json.loads(MODULE.DEFAULT_MEASUREMENTS.read_text())
            measurements["native_inputs"]["protocol_sha256"] = "0" * 64
            modified = temporary / "bad-digest.json"
            modified.write_text(json.dumps(measurements))
            with self.assertRaisesRegex(MODULE.AdapterError, "checked-in protocol"):
                self.export(temporary / "profiles-a", measurements=modified)
            measurements = json.loads(MODULE.DEFAULT_MEASUREMENTS.read_text())
            measurements["outcomes_read"] = True
            modified = temporary / "opened.json"
            modified.write_text(json.dumps(measurements))
            with self.assertRaisesRegex(MODULE.AdapterError, "outcomes were opened"):
                self.export(temporary / "profiles-b", measurements=modified)

    def test_incomplete_score_exposure_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            measurements = json.loads(MODULE.DEFAULT_MEASUREMENTS.read_text())
            measurements["measurement"]["observed_score_values"] = 899
            measurements["measurement"]["score_missingness_rate"] = 1 / 900
            modified = temporary / "incomplete.json"
            modified.write_text(json.dumps(measurements))
            with self.assertRaisesRegex(MODULE.AdapterError, "complete score exposure"):
                self.export(temporary / "profiles", measurements=modified)

    def test_failed_qualification_remains_failed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            qualification = json.loads(MODULE.DEFAULT_QUALIFICATION.read_text())
            qualification["passed"] = False
            modified_qualification = temporary / "qualification.json"
            modified_qualification.write_text(json.dumps(qualification))
            measurements = json.loads(MODULE.DEFAULT_MEASUREMENTS.read_text())
            measurements["native_inputs"]["qualification_sha256"] = hashlib.sha256(
                modified_qualification.read_bytes()
            ).hexdigest()
            modified_measurements = temporary / "measurements.json"
            modified_measurements.write_text(json.dumps(measurements))
            outputs = self.export(
                temporary / "profiles",
                measurements=modified_measurements,
                qualification=modified_qualification,
            )
            profile = json.loads(outputs[0].read_text())
            checks = {check["check_id"]: check for check in profile["qualification_checks"]}
            self.assertEqual(checks["closed-loop-outcome-support"]["status"], "fail")

    def test_existing_profile_is_not_silently_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            self.export(output)
            with self.assertRaises(FileExistsError):
                self.export(output)


if __name__ == "__main__":
    unittest.main()
