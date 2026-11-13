import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "experiments/ai-for-science/materials-science/mlip-phonon-environment-selection"
SCRIPT = STUDY / "export_environment_profiles.py"
ADAPTER_CLI = STUDY / "adapter/src/anarres_materials_adapter/cli.py"
SOURCE_PATHS = [
    STUDY / "adapter/src",
    ROOT / "packages/core/src",
    ROOT / "packages/environments/src",
]
for source_path in reversed(SOURCE_PATHS):
    sys.path.insert(0, str(source_path))
SPEC = importlib.util.spec_from_file_location("materials_mlip_profile_adapter", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
CLI_SPEC = importlib.util.spec_from_file_location("materials_mlip_adapter_cli", ADAPTER_CLI)
assert CLI_SPEC is not None and CLI_SPEC.loader is not None
CLI_MODULE = importlib.util.module_from_spec(CLI_SPEC)
CLI_SPEC.loader.exec_module(CLI_MODULE)

CANDIDATES = [
    "aimd-from-PBE-1000-npt__high_signal",
    "aimd-from-PBE-1000-npt__target_affinity",
]
EXPECTED_PROFILE_DIGESTS = {
    "aimd-from-PBE-1000-npt__high_signal": (
        "sha256:3e4a5a5bb9e2a0c5638fda2bd4593f9e65f010d1f775327644f5b7a32233b68d",
        "sha256:9280030e6d126b4696afc8b01f7db65af0ce3220a9c96543e5c1461745a192d8",
    ),
    "aimd-from-PBE-1000-npt__target_affinity": (
        "sha256:4edbc5905a80226f3047c28cb25c02eea8f34cf1b1d0a679c5c92ba1688bd20c",
        "sha256:a59cdd4c409071da6ab9073a37c2d0f4fd324501e226cd2050e89d3e850a341c",
    ),
}
NATIVE_FIXTURE = STUDY / "adapter/fixtures/omat24-qualification-slice-v1"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MaterialsMlipProfileAdapterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cargo = shutil.which("cargo")
        if cargo is None:
            user_cargo = Path.home() / ".cargo" / "bin" / "cargo"
            if user_cargo.is_file():
                cargo = str(user_cargo)
        if cargo is None:
            raise unittest.SkipTest("cargo is required for native CLI conformance")
        subprocess.run(
            [cargo, "build", "--quiet", "-p", "anarres-cli"],
            cwd=ROOT,
            check=True,
        )
        executable = "anarres.exe" if sys.platform == "win32" else "anarres"
        cls.cli = ROOT / "target" / "debug" / executable

        schema_paths = sorted((ROOT / "schemas").rglob("*.schema.json"))
        schemas = [json.loads(path.read_text()) for path in schema_paths]
        registry = Registry()
        for item in schemas:
            if isinstance(item.get("$id"), str):
                registry = registry.with_resource(item["$id"], Resource.from_contents(item))
        cls.registry = registry
        cls.input_schema = next(
            item
            for item in schemas
            if item.get("$id", "").endswith("environment-profile-input.v1.schema.json")
        )

    def export(self, output: Path) -> list[Path]:
        return MODULE.export_profiles(
            output_dir=output,
            candidate_ids=CANDIDATES,
        )

    def copy_native_fixture(self, root: Path) -> Path:
        fixture = root / "native"
        shutil.copytree(NATIVE_FIXTURE, fixture)
        return fixture

    def rewrite_native_fixture(
        self,
        fixture: Path,
        *,
        record_update=None,
        bank_update=None,
    ) -> Path:
        records_path = fixture / "structures.jsonl"
        records = [json.loads(line) for line in records_path.read_text().splitlines()]
        if record_update is not None:
            record_update(records)
        records_path.write_text(
            "".join(
                json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in records
            ),
            encoding="utf-8",
        )
        bank_path = fixture / "bank.json"
        bank = json.loads(bank_path.read_text())
        bank["records"]["sha256"] = file_sha256(records_path)
        if bank_update is not None:
            bank_update(bank)
        bank_path.write_text(json.dumps(bank, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest = fixture / "anarres.toml"
        text = manifest.read_text()
        text = text.replace(
            next(line for line in text.splitlines() if line.startswith("revision = ")),
            f'revision = "sha256:{file_sha256(bank_path)}"',
        )
        manifest.write_text(text, encoding="utf-8")
        return manifest

    def qualify_native(self, manifest: Path) -> dict:
        arguments = type("Args", (), {"manifest": manifest})()
        return CLI_MODULE.command_qualify_source(arguments)

    def test_prospective_boundary_requires_both_named_openings(self) -> None:
        complete = {
            "prospective_boundary": {
                "prospective_candidate_training_outcomes_used": True,
                "prospective_target_outcomes_used": True,
            }
        }
        self.assertTrue(CLI_MODULE.prospective_boundaries_opened(complete))
        self.assertFalse(CLI_MODULE.prospective_boundaries_opened({}))
        self.assertFalse(CLI_MODULE.prospective_boundaries_opened({"prospective_boundary": {}}))
        self.assertFalse(
            CLI_MODULE.prospective_boundaries_opened(
                {
                    "prospective_boundary": {
                        "prospective_candidate_training_outcomes_used": True,
                    }
                }
            )
        )

    def cli_run(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(self.cli), *arguments],
            cwd=ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def test_released_bank_exports_compatible_real_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            inputs = self.export(temporary / "inputs")
            self.assertEqual([path.stem.split(".profile-input")[0] for path in inputs], CANDIDATES)

            profiles = []
            for profile_input in inputs:
                payload = json.loads(profile_input.read_text())
                Draft202012Validator(self.input_schema, registry=self.registry).validate(payload)
                checks = {check["check_id"]: check for check in payload["qualification_checks"]}
                self.assertEqual(checks["measurements-complete"]["status"], "pass")
                self.assertEqual(checks["candidate-outcomes-sealed"]["status"], "pass")
                self.assertEqual(checks["final-panel-frozen"]["status"], "pass")
                self.assertEqual(checks["final-panel-frozen"]["severity"], "error")
                self.assertEqual(len(payload["artifacts"]), 7)
                self.assertNotIn("uncertainty", payload["coordinates"][0])
                coordinates = {
                    coordinate["name"]: coordinate for coordinate in payload["coordinates"]
                }
                self.assertEqual(
                    set(coordinates),
                    {
                        "chemical_system_entropy",
                        "effective_signal_coverage",
                        "mean_target_affinity",
                        "neighbor_edges_per_atom",
                        "processed_atom_budget",
                        "signal_density_per_atom",
                    },
                )
                self.assertEqual(
                    coordinates["signal_density_per_atom"]["unit"],
                    "loss_weighted_residual_per_atom",
                )
                self.assertEqual(coordinates["processed_atom_budget"]["unit"], "processed_atoms")

                measured = (
                    temporary
                    / "profiles"
                    / profile_input.name.replace(".profile-input", ".profile")
                )
                measured.parent.mkdir(parents=True, exist_ok=True)
                self.cli_run("measure", str(profile_input), "--output", str(measured))
                profile = json.loads(measured.read_text())
                self.assertTrue(profile["ready"])
                expected_input, expected_profile = EXPECTED_PROFILE_DIGESTS[
                    profile["environment_id"]
                ]
                self.assertEqual(profile["input_digest"], expected_input)
                self.assertEqual(profile["profile_digest"], expected_profile)
                profiles.append(measured)

            report = self.cli_run("design", *(str(path) for path in profiles), "--json")
            design = json.loads(report.stdout)
            self.assertTrue(design["compatible"])
            self.assertEqual(design["candidate_count"], 2)
            self.assertEqual(
                design["coordinate_ranges"]["processed_atom_budget"],
                {"minimum": 50000.0, "maximum": 50000.0},
            )
            self.assertLess(
                design["coordinate_ranges"]["signal_density_per_atom"]["minimum"],
                design["coordinate_ranges"]["signal_density_per_atom"]["maximum"],
            )

    def test_output_is_byte_stable_and_native_digests_are_pinned(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            first = self.export(temporary / "first")
            second = self.export(temporary / "second")
            self.assertEqual(
                [path.read_bytes() for path in first], [path.read_bytes() for path in second]
            )
            self.assertEqual(
                [file_sha256(path) for path in first],
                [
                    "cea3c0aae6883b74d092fbd0a3fa494efdc444541e7be5db15a6ae1c6f994083",
                    "5d24cceb8db6e1ca3e9fa6570d27070aa9ea6ca9f1af9ec705b98441423f12d2",
                ],
            )

    def test_missing_or_modified_native_evidence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            with self.assertRaisesRegex(MODULE.AdapterError, "missing"):
                MODULE.export_profiles(
                    bank_path=temporary / "missing.json",
                    output_dir=temporary / "missing-output",
                    candidate_ids=CANDIDATES,
                )

            source = json.loads(MODULE.DEFAULT_SOURCE.read_text())
            source["construction_reservoir"]["archive"]["sha256"] = "0" * 64
            modified = temporary / "SOURCE_QUALIFICATION.json"
            modified.write_text(json.dumps(source))
            with self.assertRaisesRegex(MODULE.AdapterError, "digest differs"):
                MODULE.export_profiles(
                    source_path=modified,
                    output_dir=temporary / "modified-output",
                    candidate_ids=CANDIDATES,
                )

    def test_zero_and_negative_measurements_are_not_coerced(self) -> None:
        self.assertEqual(MODULE.finite_number({"candidate_id": "x", "value": 0}, "value"), 0.0)
        self.assertEqual(
            MODULE.finite_number({"candidate_id": "x", "value": -0.25}, "value"),
            -0.25,
        )

    def test_cli_rejects_changed_coordinate_definition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            inputs = self.export(temporary / "inputs")
            changed = json.loads(inputs[1].read_text())
            changed["coordinates"][0]["definition"]["revision"] = "v2-incompatible"
            changed_input = temporary / "changed.profile-input.json"
            changed_input.write_text(json.dumps(changed, indent=2, sort_keys=True) + "\n")

            first_profile = temporary / "first.profile.json"
            changed_profile = temporary / "changed.profile.json"
            self.cli_run("measure", str(inputs[0]), "--output", str(first_profile))
            self.cli_run("measure", str(changed_input), "--output", str(changed_profile))
            result = self.cli_run(
                "design", str(first_profile), str(changed_profile), "--json", check=False
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("different coordinate definitions", result.stdout + result.stderr)

    def test_existing_profiles_are_not_silently_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            self.export(output)
            with self.assertRaises(FileExistsError):
                self.export(output)

    def test_adapter_descriptor_and_status_preserve_the_study_boundary(self) -> None:
        descriptor = CLI_MODULE.adapter_descriptor()
        self.assertEqual(descriptor["schema_version"], "anarres.adapter-descriptor.v1")
        self.assertEqual(descriptor["name"], "materials")
        self.assertEqual(descriptor["version"], "0.7.0")
        self.assertEqual(descriptor["protocol_version"], 2)
        self.assertEqual(
            descriptor["measurement_contracts"],
            ["materials.mlip-phonon-candidate-measurement.v2"],
        )
        self.assertEqual(descriptor["capabilities"], sorted(descriptor["capabilities"]))
        self.assertEqual(descriptor["source_formats"], ["atomistic-candidate-bank-v1"])

        args = type("Args", (), {"repository": ROOT})()
        status = CLI_MODULE.command_status(args)
        self.assertEqual(status["candidate_count"], 16)
        self.assertTrue(status["measurements_complete"])
        self.assertTrue(status["candidate_outcomes_opened"])
        self.assertTrue(status["final_training_panel_frozen"])
        self.assertTrue(status["decision_protocol_frozen"])
        self.assertTrue(status["regression_protocol_frozen"])
        self.assertTrue(status["predictive_evidence_available"])
        self.assertEqual(status["prospective_test_status"], "prospective_test_scored")
        self.assertEqual(
            status["training_qualification_status"],
            "complete_before_final_candidate_training",
        )
        self.assertEqual(status["selected_learning_rate"], 1e-4)
        self.assertTrue(status["starting_target_features_complete"])
        self.assertEqual(
            status["final_training_contract_status"],
            "frozen_before_final_candidate_training",
        )
        self.assertTrue(status["target_regression_features_frozen"])
        self.assertTrue(status["development_modeling_protocol_frozen"])
        self.assertTrue(status["prospective_predictions_frozen"])
        self.assertEqual(status["native_source_format"], "atomistic-candidate-bank-v1")
        self.assertFalse(status["policy_probe_available"])
        self.assertEqual(
            status["next_gate"],
            "freeze support-aware abstention and expand development support",
        )

    def test_status_validates_large_feature_artifact_without_deserializing_it(self) -> None:
        exporter = CLI_MODULE.load_exporter(ROOT)
        target_features = CLI_MODULE.target_regression_features_path(ROOT).resolve()
        opened: list[Path] = []

        class ExporterProxy:
            DEFAULT_BANK = exporter.DEFAULT_BANK
            DEFAULT_VALIDATION = exporter.DEFAULT_VALIDATION

            @staticmethod
            def read_object(path: Path):
                resolved = Path(path).resolve()
                opened.append(resolved)
                if resolved == target_features:
                    raise AssertionError("status deserialized the large target-feature artifact")
                return exporter.read_object(path)

            @staticmethod
            def export_profiles(**kwargs):
                return exporter.export_profiles(**kwargs)

        original_loader = CLI_MODULE.load_exporter
        try:
            CLI_MODULE.load_exporter = lambda _repository: ExporterProxy()
            args = type("Args", (), {"repository": ROOT})()
            status = CLI_MODULE.command_status(args)
        finally:
            CLI_MODULE.load_exporter = original_loader

        self.assertTrue(status["target_regression_features_frozen"])
        self.assertNotIn(target_features, opened)

    def test_status_rejects_an_unbound_target_feature_artifact(self) -> None:
        original_sha256 = CLI_MODULE.sha256
        target_features = CLI_MODULE.target_regression_features_path(ROOT).resolve()

        def changed_digest(path: Path) -> str:
            if Path(path).resolve() == target_features:
                return "0" * 64
            return original_sha256(path)

        try:
            CLI_MODULE.sha256 = changed_digest
            args = type("Args", (), {"repository": ROOT})()
            status = CLI_MODULE.command_status(args)
        finally:
            CLI_MODULE.sha256 = original_sha256

        self.assertFalse(status["target_regression_features_frozen"])

    def test_adapter_reports_frozen_decision_and_regression_protocol(self) -> None:
        args = type("Args", (), {"repository": ROOT})()
        report = CLI_MODULE.command_protocol(args)

        self.assertEqual(report["schema_version"], "anarres.materials-decision-protocol-report.v1")
        self.assertEqual(report["evidence_tier"], "frozen_pre_outcome_protocol")
        self.assertFalse(report["predictive_evidence_available"])
        self.assertEqual(report["candidate_panel"]["candidates"], 16)
        self.assertEqual(report["candidate_panel"]["development_environments"], 12)
        self.assertEqual(report["candidate_panel"]["prospective_environments"], 4)
        self.assertEqual(len(report["baseline"]["ranking"]), 16)
        self.assertEqual(
            report["regression_evaluation"]["primary_endpoint"]["name"],
            "frequency_error_regression",
        )
        self.assertFalse(report["training_qualification"]["included_in_final_panel"])
        self.assertFalse(report["training_qualification"]["uses_phonon_target_outcomes"])
        self.assertEqual(report["training_qualification"]["learning_rates"], [1e-5, 3e-5, 1e-4])
        self.assertEqual(report["training_qualification"]["selected_learning_rate"], 1e-4)
        self.assertEqual(report["final_training_contract"]["development_environments"], 12)
        self.assertEqual(report["final_training_contract"]["prospective_environments"], 4)
        self.assertEqual(report["development_modeling"]["target_feature_pairs"], 1200)
        self.assertEqual(len(report["development_modeling"]["aggregate_predictors"]), 4)
        self.assertEqual(len(report["development_modeling"]["regression_models"]), 5)
        self.assertEqual(report["development_results"]["aggregate_model"], "signal_density_only")
        self.assertEqual(report["development_results"]["regression_model"], "full_numeric")
        self.assertEqual(report["prospective_freeze"]["forecast_counts"]["environment_curves"], 4)
        self.assertEqual(
            report["prospective_freeze"]["forecast_counts"]["target_regression_probabilities"],
            200,
        )
        self.assertTrue(all(value is False for value in report["outcome_boundary"].values()))

    def test_adapter_reports_scored_prospective_result_and_evidence_boundary(self) -> None:
        args = type("Args", (), {"repository": ROOT})()
        report = CLI_MODULE.command_results(args)

        self.assertEqual(report["schema_version"], "anarres.materials-prospective-results.v1")
        self.assertEqual(report["evidence_tier"], "prospective_test_scored")
        self.assertEqual(report["counts"]["evaluation_records"], 1600)
        self.assertEqual(report["aggregate_utility"]["best_environment_decisions"], 0.0)
        self.assertAlmostEqual(report["target_regressions"]["roc_auc"], 0.4937483373)
        diagnostic = report["post_prospective_diagnostic"]
        self.assertFalse(diagnostic["support_guard_prespecified"])
        self.assertTrue(diagnostic["would_abstain_at_all_budgets"])

    def test_adapter_runs_outside_the_repository_and_core_doctor_accepts_it(self) -> None:
        if sys.platform == "win32":
            self.skipTest("executable wrapper fixture uses POSIX permissions")
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            executable = temporary / "anarres-materials"
            executable.write_text(
                f"#!{sys.executable}\n"
                "import runpy\n"
                f"runpy.run_path({str(ADAPTER_CLI)!r}, run_name='__main__')\n"
            )
            executable.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = os.pathsep.join([str(temporary), environment.get("PATH", "")])
            environment["PYTHONPATH"] = os.pathsep.join(
                [
                    str(ROOT / "packages/core/src"),
                    str(ROOT / "packages/environments/src"),
                    str(STUDY / "adapter/src"),
                    environment.get("PYTHONPATH", ""),
                ]
            )

            doctor = subprocess.run(
                [str(self.cli), "adapter", "doctor", "materials", "--json"],
                cwd=temporary,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(doctor.stdout)
            self.assertTrue(report["valid"])
            self.assertEqual(report["descriptor"]["domain"], "materials-interatomic-potentials")

            status = subprocess.run(
                [
                    str(self.cli),
                    "materials",
                    "status",
                    "--repository",
                    str(ROOT),
                    "--json",
                ],
                cwd=temporary,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(status.returncode, 0, status.stderr)
            payload = json.loads(status.stdout)
            self.assertEqual(payload["candidate_count"], 16)
            self.assertTrue(payload["candidate_outcomes_opened"])

    def test_native_omat24_source_qualifies_without_opening_outcomes(self) -> None:
        first = self.qualify_native(NATIVE_FIXTURE / "anarres.toml")
        second = self.qualify_native(NATIVE_FIXTURE / "anarres.toml")
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "qualified")
        self.assertEqual(first["records"], 2)
        self.assertEqual(first["materials"], 2)
        self.assertEqual(first["atoms"], 8)
        self.assertEqual(first["neighbor_edges"], 438)
        self.assertEqual(first["record_status_counts"]["valid"], 2)
        self.assertEqual(first["claim_bank"]["records"], 80_000)
        self.assertTrue(first["membership_sha256"].startswith("sha256:"))
        self.assertTrue(first["content_sha256"].startswith("sha256:"))
        self.assertFalse(first["policy_probe_available"])
        self.assertFalse(first["training_started"])
        self.assertFalse(first["candidate_outcomes_opened"])

        bank = json.loads((NATIVE_FIXTURE / "bank.json").read_text())
        validation = json.loads((STUDY / "FULL_MEASUREMENT_VALIDATION.json").read_text())
        contract = json.loads((STUDY / "FINAL_TRAINING_CONTRACT.json").read_text())
        target_roles = json.loads((STUDY / "TARGET_ROLES.json").read_text())
        expected_targets = {
            material_id for members in target_roles["roles"].values() for material_id in members
        }
        self.assertEqual(bank["claim_bank"]["manifest_sha256"], validation["manifest_sha256"])
        self.assertEqual(
            bank["starting_checkpoint"]["sha256"], contract["starting_checkpoint"]["sha256"]
        )
        self.assertEqual(set(bank["exclusions"]["evaluation_material_ids"]), expected_targets)
        self.assertEqual(
            bank["claim_bank"]["construction_script_sha256"],
            file_sha256(STUDY / "build_measurement_pool.py"),
        )

    def test_native_source_preserves_scientific_zero_and_unstable_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.copy_native_fixture(Path(directory))

            def update(records):
                records[0]["record_status"] = "scientific_zero"
                records[0]["energy_ev"] = 0.0
                records[1]["record_status"] = "unstable"

            report = self.qualify_native(self.rewrite_native_fixture(fixture, record_update=update))
        self.assertEqual(report["record_status_counts"]["scientific_zero"], 1)
        self.assertEqual(report["record_status_counts"]["unstable"], 1)

    def test_native_source_rejects_infrastructure_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.copy_native_fixture(Path(directory))
            manifest = self.rewrite_native_fixture(
                fixture,
                record_update=lambda rows: rows[0].update(
                    {"record_status": "infrastructure_failure"}
                ),
            )
            with self.assertRaisesRegex(ValueError, "infrastructure failure"):
                self.qualify_native(manifest)

    def test_native_source_rejects_structure_identity_and_budget_errors(self) -> None:
        cases = [
            (lambda rows: rows[1].update({"record_id": rows[0]["record_id"]}), "duplicate"),
            (lambda rows: rows[0].pop("stress_ev_per_angstrom3"), "missing fields"),
            (lambda rows: rows[0].update({"positions_angstrom": [[0.0, 0.0, 0.0]]}), "positions"),
            (lambda rows: rows[0]["positions_angstrom"][0].__setitem__(0, float("nan")), "finite"),
            (lambda rows: rows[0].update({"source_family": "unknown-source"}), "source family"),
            (lambda rows: rows[0].update({"material_id": "mp-6356"}), "overlaps"),
        ]
        for update, message in cases:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                fixture = self.copy_native_fixture(Path(directory))
                manifest = self.rewrite_native_fixture(fixture, record_update=update)
                with self.assertRaisesRegex(ValueError, message):
                    self.qualify_native(manifest)

        bank_cases = [
            (lambda bank: bank["records"].update({"atoms": 9}), "atom total"),
            (lambda bank: bank["records"].update({"neighbor_edges": 439}), "neighbor-edge total"),
        ]
        for update, message in bank_cases:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                fixture = self.copy_native_fixture(Path(directory))
                manifest = self.rewrite_native_fixture(fixture, bank_update=update)
                with self.assertRaisesRegex(ValueError, message):
                    self.qualify_native(manifest)

    def test_native_source_rejects_property_unit_checkpoint_and_runtime_mismatch(self) -> None:
        cases = [
            (lambda bank: bank["properties"].update({"force_unit": "hartree/bohr"}), "force_unit"),
            (
                lambda bank: bank["properties"].update({"required": ["energy", "forces"]}),
                "required",
            ),
            (
                lambda bank: bank["starting_checkpoint"].update({"sha256": "0" * 64}),
                "starting checkpoint",
            ),
            (
                lambda bank: bank["measurement_contract"]["calculator"].update(
                    {"revision": "0" * 40}
                ),
                "calculator revision",
            ),
        ]
        for update, message in cases:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                fixture = self.copy_native_fixture(Path(directory))
                manifest = self.rewrite_native_fixture(fixture, bank_update=update)
                with self.assertRaisesRegex(ValueError, message):
                    self.qualify_native(manifest)

    def test_native_source_revision_and_license_are_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self.copy_native_fixture(Path(directory))
            manifest = fixture / "anarres.toml"
            manifest.write_text(
                manifest.read_text().replace("sha256:f4066a5d", "sha256:00000000"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "source revision"):
                self.qualify_native(manifest)

        with tempfile.TemporaryDirectory() as directory:
            fixture = self.copy_native_fixture(Path(directory))
            manifest = fixture / "anarres.toml"
            manifest.write_text(
                manifest.read_text().replace('license = "CC BY 4.0"', 'license = "unknown"'),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "manifest license"):
                self.qualify_native(manifest)

    def test_native_source_qualification_does_not_open_released_outcomes(self) -> None:
        original = CLI_MODULE.prospective_outcomes_path
        try:
            CLI_MODULE.prospective_outcomes_path = mock.Mock(
                side_effect=AssertionError("qualification opened prospective outcomes")
            )
            report = self.qualify_native(NATIVE_FIXTURE / "anarres.toml")
        finally:
            CLI_MODULE.prospective_outcomes_path = original
        self.assertFalse(report["candidate_outcomes_opened"])

    def test_adapter_verify_reuses_the_native_exporter(self) -> None:
        args = type("Args", (), {"repository": ROOT})()
        report = CLI_MODULE.command_verify(args)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["profiles_checked"], 16)
        self.assertTrue(report["deterministic"])
        self.assertEqual(report["measurement_records"], 80_000)
        self.assertEqual(report["measurement_shards_pinned"], 8)
        self.assertFalse(report["candidate_outcomes_sealed"])
        self.assertTrue(report["profile_outcome_boundary_preserved"])
        self.assertTrue(report["final_training_panel_frozen"])
        self.assertEqual(report["prospective_test_status"], "prospective_test_scored")
        self.assertTrue(report["prospective_result_chain_valid"])


if __name__ == "__main__":
    unittest.main()
