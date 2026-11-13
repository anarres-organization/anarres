import json
import os
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "experiments/ai-for-science/molecular-design/reaction-environment-selection"
SOURCE = STUDY / "src"
sys.path.insert(0, str(SOURCE))
SHARED_SOURCES = [
    ROOT / "packages/core/src",
    ROOT / "packages/environments/src",
]
for shared_source in reversed(SHARED_SOURCES):
    sys.path.insert(0, str(shared_source))

from anarres_molecular_adapter import cli  # noqa: E402
from anarres_molecular_adapter import probe as molecular_probe  # noqa: E402
from anarres_molecular_adapter import source as molecular_source  # noqa: E402

BINARY = ROOT / "target/debug/anarres"


class MolecularCliTest(unittest.TestCase):
    def test_descriptor_is_schema_valid_sorted_and_side_effect_free(self) -> None:
        descriptor = cli.adapter_descriptor()
        schema = json.loads(
            (ROOT / "schemas/adapters/adapter-descriptor.v1.schema.json").read_text()
        )
        Draft202012Validator(schema).validate(descriptor)
        self.assertEqual(descriptor["name"], "molecular")
        self.assertEqual(descriptor["executable"], "anarres-molecular")
        self.assertEqual(descriptor["capabilities"], sorted(set(descriptor["capabilities"])))
        self.assertIn("policy-probe", descriptor["capabilities"])
        self.assertIn("acquisition-results", descriptor["capabilities"])
        self.assertEqual(
            descriptor["measurement_contracts"],
            [
                "q07820-starting-policy-endpoint-qualification-v2",
                "rxnflow-q07820-bank-v4",
            ],
        )
        self.assertEqual(descriptor["source_formats"], ["rxnflow-molecular-environment-v1"])

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def create_native_source(
        self,
        destination: Path,
        *,
        building_blocks: str = "CC\tbb-1\nCO\tbb-2\n",
        target_id: str = "Q07820",
    ) -> str:
        destination.mkdir()
        blocks = destination / "chemistry/building_blocks.smi"
        blocks.parent.mkdir()
        blocks.write_text(building_blocks, encoding="utf-8")
        templates = destination / "chemistry/reaction_templates.json"
        self._write_json(
            templates,
            {
                "templates": [
                    {
                        "template_id": "rxn-1",
                        "reaction_smarts": "[C:1].[O:2]>>[C:1][O:2]",
                        "compatible_building_block_ids": ["bb-1", "bb-2"],
                    }
                ]
            },
        )
        prepared_environment = destination / "prepared/environment"
        prepared_environment.mkdir(parents=True)
        (prepared_environment / "environment.bin").write_bytes(b"qualified-rxnflow-environment")
        preparation = destination / "prepared/environment-report.json"
        self._write_json(
            preparation,
            {
                "status": "qualified",
                "building_blocks_sha256": molecular_source.sha256_file(blocks),
                "reaction_templates_sha256": molecular_source.sha256_file(templates),
                "prepared_environment_sha256": molecular_source.tree_digest(prepared_environment),
                "building_block_count": 2,
                "reaction_template_count": 1,
            },
        )
        replay = destination / "candidate/replay.json"
        replay.parent.mkdir()
        trajectory_ids = ["train-001", "train-002"]
        self._write_json(
            replay,
            {
                "artifact_type": "anarres.rxnflow-replay-bank.v1",
                "items": [
                    {
                        "trajectory_id": "train-001",
                        "molecule_id": "mol-1",
                        "canonical_smiles": "CCO",
                        "building_block_ids": ["bb-1", "bb-2"],
                        "reaction_template_ids": ["rxn-1"],
                    },
                    {
                        "trajectory_id": "train-002",
                        "molecule_id": "mol-2",
                        "canonical_smiles": "COC",
                        "building_block_ids": ["bb-1"],
                        "reaction_template_ids": ["rxn-1"],
                    },
                ],
            },
        )
        policy = destination / "policy/weights.pt"
        policy.parent.mkdir()
        policy.write_bytes(b"test-policy-weights")
        target = destination / "target"
        target.mkdir()
        receptor = target / "receptor.pdbqt"
        ligand = target / "reference.sdf"
        receptor.write_text("RECEPTOR\n", encoding="utf-8")
        ligand.write_text("REFERENCE\n", encoding="utf-8")
        self._write_json(
            target / "target_manifest.json",
            {
                "target_id": target_id,
                "receptor_pdbqt": receptor.name,
                "reference_ligand": ligand.name,
                "fixture_sha256": {
                    "prepared_receptor": molecular_source.sha256_file(receptor),
                    "reference_ligand": molecular_source.sha256_file(ligand),
                },
            },
        )
        endpoint_assets = {
            "protein": "protein.pdb",
            "pocket": "pocket.pdb",
            "reference_actives": "reference-actives.sdf",
            "reference_interaction_scores": "reference-interactions.json",
            "thresholds": "thresholds.json",
        }
        for name in endpoint_assets.values():
            (target / name).write_text(f"fixture {name}\n", encoding="utf-8")
        contracts = destination / "contracts"
        contracts.mkdir()
        self._write_json(
            contracts / "oracle.json",
            {
                "target_id": target_id,
                "runtime": "vina-test-runtime",
                "failure_semantics": {
                    "scientific_zero": [
                        "invalid_chemistry",
                        "filter_rejection",
                        "docking_failure",
                        "timeout",
                    ],
                    "infrastructure_failure": ["missing_receptor", "toolchain_failure"],
                    "missing_score": "missing",
                },
                "outcome_states": sorted(molecular_source.REQUIRED_OUTCOME_STATES),
            },
        )
        self._write_json(contracts / "filters.json", {"target_id": target_id, "version": "test-v1"})
        self._write_json(contracts / "docking.json", {"target_id": target_id, "version": "test-v1"})
        self._write_json(
            contracts / "probe.json",
            {"target_id": target_id, "attempts": 4, "seed": 20261126, "batch_size": 2},
        )
        membership = (
            __import__("hashlib")
            .sha256(("\n".join(sorted(trajectory_ids)) + "\n").encode("utf-8"))
            .hexdigest()
        )
        declaration = {
            "schema_version": "anarres.molecular-environment-source.v1",
            "environment_id": "fixture-molecular-environment",
            "target_id": target_id,
            "duplicate_policy": "reject_exact_canonical_smiles",
            "reaction_environment": {
                "building_blocks": {
                    "path": blocks.relative_to(destination).as_posix(),
                    "sha256": molecular_source.sha256_file(blocks),
                },
                "reaction_templates": {
                    "path": templates.relative_to(destination).as_posix(),
                    "sha256": molecular_source.sha256_file(templates),
                },
                "prepared_environment": {
                    "path": prepared_environment.relative_to(destination).as_posix(),
                    "sha256": molecular_source.tree_digest(prepared_environment),
                },
                "preparation_report": {
                    "path": preparation.relative_to(destination).as_posix(),
                    "sha256": molecular_source.sha256_file(preparation),
                },
            },
            "candidate_replay_bank": {
                "path": replay.relative_to(destination).as_posix(),
                "sha256": molecular_source.sha256_file(replay),
                "item_count": 2,
                "membership_sha256": membership,
                "duplicate_molecule_policy": "retain_distinct_trajectory_ids",
            },
            "starting_policy": {
                "path": policy.relative_to(destination).as_posix(),
                "sha256": molecular_source.sha256_file(policy),
                "policy_id": "fixture-policy",
                "revision": f"sha256:{molecular_source.sha256_file(policy)}",
            },
            "target": {
                "prepared_target": {
                    "path": target.relative_to(destination).as_posix(),
                    "sha256": molecular_source.tree_digest(target),
                },
                "manifest": "target_manifest.json",
                "endpoint_assets": {
                    key: {
                        "path": (target / name).relative_to(destination).as_posix(),
                        "sha256": molecular_source.sha256_file(target / name),
                    }
                    for key, name in endpoint_assets.items()
                },
            },
            "contracts": {
                name: {
                    "path": (contracts / f"{name}.json").relative_to(destination).as_posix(),
                    "sha256": molecular_source.sha256_file(contracts / f"{name}.json"),
                }
                for name in ("oracle", "filters", "docking", "probe")
            },
            "partitions": {
                "training_ids": trajectory_ids,
                "evaluation_attempt_ids": ["eval-001", "eval-002", "eval-003", "eval-004"],
            },
            "sources": [
                {
                    "name": "fixture-rxnflow",
                    "revision": "test-revision",
                    "license": "Apache-2.0",
                    "paths": [
                        "chemistry/building_blocks.smi",
                        "chemistry/reaction_templates.json",
                        "prepared/environment",
                        "candidate/replay.json",
                        "policy/weights.pt",
                        "target",
                        "contracts/oracle.json",
                        "contracts/filters.json",
                        "contracts/docking.json",
                        "contracts/probe.json",
                    ],
                }
            ],
        }
        self._write_json(destination / molecular_source.SOURCE_FILE, declaration)
        return molecular_source.bundle_digest(destination)

    def source_manifest(self, source: Path, digest: str) -> Path:
        manifest = source / "anarres.toml"
        manifest.write_text(
            "\n".join(
                [
                    'schema_version = "anarres.environment-source.v1"',
                    'environment_id = "fixture-molecular-environment"',
                    'domain = "molecular-design"',
                    'adapter = "molecular"',
                    'adapter_version = "0.4.0"',
                    'native_format = "rxnflow-molecular-environment-v1"',
                    "",
                    "[source]",
                    'uri = "."',
                    f'revision = "sha256:{digest}"',
                    'license = "mixed-public-sources"',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return manifest

    def test_native_source_qualification_precedes_measurement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "molecular-environment"
            digest = self.create_native_source(source)
            manifest = self.source_manifest(source, digest)
            with mock.patch("subprocess.run", side_effect=AssertionError("runtime invoked")):
                result = cli.command_qualify_source(type("Args", (), {"manifest": manifest})())
        self.assertEqual(result["status"], "qualified")
        self.assertEqual(result["target_id"], "Q07820")
        self.assertEqual(result["building_block_count"], 2)
        self.assertEqual(result["candidate_replay_items"], 2)
        self.assertEqual(result["probe_attempts"], 4)
        self.assertTrue(result["policy_probe_available"])
        self.assertFalse(result["training_outcomes_opened"])
        self.assertFalse(result["probe_outcomes_opened"])

    def test_native_source_rejects_malformed_molecule_and_duplicate_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            malformed = Path(temporary) / "malformed"
            self.create_native_source(malformed, building_blocks="C1(\tbb-1\nCO\tbb-2\n")
            with self.assertRaisesRegex(ValueError, "malformed SMILES"):
                molecular_source.qualify_source(malformed)
            duplicate = Path(temporary) / "duplicate"
            self.create_native_source(duplicate, building_blocks="CC\tbb-1\nCO\tbb-1\n")
            with self.assertRaisesRegex(ValueError, "duplicate building-block identity"):
                molecular_source.qualify_source(duplicate)

    def test_native_source_rejects_wrong_target_replay_and_missing_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            wrong_target = Path(temporary) / "wrong-target"
            self.create_native_source(wrong_target)
            oracle = wrong_target / "contracts/oracle.json"
            value = json.loads(oracle.read_text())
            value["target_id"] = "OTHER"
            self._write_json(oracle, value)
            declaration = json.loads((wrong_target / molecular_source.SOURCE_FILE).read_text())
            declaration["contracts"]["oracle"]["sha256"] = molecular_source.sha256_file(oracle)
            self._write_json(wrong_target / molecular_source.SOURCE_FILE, declaration)
            with self.assertRaisesRegex(ValueError, "oracle contract targets another system"):
                molecular_source.qualify_source(wrong_target)

            wrong_replay = Path(temporary) / "wrong-replay"
            self.create_native_source(wrong_replay)
            declaration = json.loads((wrong_replay / molecular_source.SOURCE_FILE).read_text())
            declaration["candidate_replay_bank"]["membership_sha256"] = "0" * 64
            self._write_json(wrong_replay / molecular_source.SOURCE_FILE, declaration)
            with self.assertRaisesRegex(ValueError, "replay membership digest"):
                molecular_source.qualify_source(wrong_replay)

            missing_filter = Path(temporary) / "missing-filter"
            self.create_native_source(missing_filter)
            (missing_filter / "contracts/filters.json").unlink()
            with self.assertRaisesRegex(ValueError, "filters contract is missing"):
                molecular_source.qualify_source(missing_filter)

    def test_native_source_rejects_prepared_target_drift_and_source_revision_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "molecular-environment"
            digest = self.create_native_source(source)
            manifest = self.source_manifest(source, digest)
            receptor = source / "target/receptor.pdbqt"
            receptor.write_text("CHANGED\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "prepared target digest"):
                molecular_source.qualify_source(source)
            with self.assertRaisesRegex(ValueError, "observed sha256"):
                cli.command_qualify_source(type("Args", (), {"manifest": manifest})())

    def test_probe_plan_binds_bounded_seeded_endpoint_without_running_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            self.create_native_source(source)
            repository = root / "repository"
            study = (
                repository
                / "experiments/ai-for-science/molecular-design/reaction-environment-selection"
            )
            scripts = study / "scripts"
            scripts.mkdir(parents=True)
            for name in (
                "sample_endpoint_policy.py",
                "dock_endpoint_panel.py",
                "score_endpoint_metrics.py",
                "score_qualifying_hits.py",
                "apply_starting_policy_endpoint_gate.py",
            ):
                (scripts / name).write_text("raise SystemExit('must not execute')\n")
            policy_sha = molecular_source.sha256_file(source / "policy/weights.pt")
            matched = {
                "starting_policy": {"weights_only_sha256": policy_sha},
                "evaluation": {
                    "attempts_per_policy_seed_checkpoint": 4,
                    "seeds": {"20261108": {"0": 20261126}},
                },
            }
            endpoint = {"contract": "fixture-endpoint-v1"}
            self._write_json(study / "MATCHED_TRAINING_EVALUATION_CONTRACT_V1.json", matched)
            self._write_json(
                study / "STARTING_POLICY_ENDPOINT_QUALIFICATION_CONTRACT_V2.json", endpoint
            )
            target = source / "target"
            probe_path = source / "contracts/probe.json"
            self._write_json(
                probe_path,
                {
                    "target_id": "Q07820",
                    "attempts": 4,
                    "seed": 20261126,
                    "batch_size": 2,
                    "training_seed": 20261108,
                    "checkpoint_step": 0,
                    "arm": "warm_start",
                    "matched_contract_sha256": molecular_source.sha256_file(
                        study / "MATCHED_TRAINING_EVALUATION_CONTRACT_V1.json"
                    ),
                    "endpoint_contract_sha256": molecular_source.sha256_file(
                        study / "STARTING_POLICY_ENDPOINT_QUALIFICATION_CONTRACT_V2.json"
                    ),
                },
            )
            declaration_path = source / molecular_source.SOURCE_FILE
            declaration = json.loads(declaration_path.read_text())
            declaration["contracts"]["probe"]["sha256"] = molecular_source.sha256_file(probe_path)
            declaration["target"]["prepared_target"]["sha256"] = molecular_source.tree_digest(
                target
            )
            self._write_json(declaration_path, declaration)
            output = root / "probe"
            plan = molecular_probe.build_probe_plan(
                source_root=source,
                repository=repository,
                policy_id="fixture-policy",
                policy_revision=f"sha256:{policy_sha}",
                output=output,
                sampler_python=Path(sys.executable),
                oracle_python=Path(sys.executable),
                device="cpu",
                docking_jobs=2,
                metric_jobs=2,
            )
            second = molecular_probe.build_probe_plan(
                source_root=source,
                repository=repository,
                policy_id="fixture-policy",
                policy_revision=f"sha256:{policy_sha}",
                output=output,
                sampler_python=Path(sys.executable),
                oracle_python=Path(sys.executable),
                device="cpu",
                docking_jobs=2,
                metric_jobs=2,
            )
        self.assertEqual(plan, second)
        self.assertEqual(plan["attempts"], 4)
        self.assertEqual(plan["evaluation_seed"], 20261126)
        self.assertEqual(
            [stage["name"] for stage in plan["commands"]],
            ["sample", "dock", "metrics", "score", "gate"],
        )
        self.assertFalse(plan["outcomes_opened"])

    def test_probe_execution_resumes_from_verified_stage_digests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            first = output / "first.json"
            second = output / "second.json"
            plan = {
                "plan_sha256": "plan-test",
                "commands": [
                    {
                        "name": "first",
                        "command": [
                            sys.executable,
                            "-c",
                            f"from pathlib import Path; Path(r'{first}').write_text('one')",
                        ],
                        "outputs": [str(first)],
                    },
                    {
                        "name": "second",
                        "command": [
                            sys.executable,
                            "-c",
                            f"from pathlib import Path; Path(r'{second}').write_text('two')",
                        ],
                        "outputs": [str(second)],
                    },
                ],
            }
            initial = molecular_probe.execute_probe_plan(plan, output)
            resumed = molecular_probe.execute_probe_plan(plan, output)
        self.assertEqual(initial, resumed)
        self.assertEqual(initial["status"], "complete")
        self.assertEqual(len(initial["stages"]), 2)

    def test_status_reports_passed_confirmation_and_sealed_outcomes(self) -> None:
        result = cli.command_status(type("Args", (), {"repository": ROOT})())
        self.assertEqual(result["target_id"], "Q07820")
        self.assertEqual(result["bank_count"], 6)
        self.assertTrue(result["bank_confirmation_passed"])
        self.assertTrue(result["endpoint_qualification_passed"])
        self.assertEqual(result["endpoint_qualification_status"], "passed")
        self.assertEqual(result["endpoint_qualifying_attempts"], 22)
        self.assertEqual(result["endpoint_unique_qualifying_molecules"], 16)
        self.assertEqual(result["endpoint_infrastructure_failures"], 0)
        self.assertTrue(result["matched_training_contract_frozen"])
        self.assertTrue(result["profiles_ready"])
        self.assertTrue(result["development_training_authorized"])
        self.assertFalse(result["training_outcomes_opened"])
        self.assertEqual(result["confirmation_rule"], "selector_fidelity")
        self.assertEqual(result["failed_confirmation_checks"], [])

    def test_profile_reuses_native_exporter_without_rho_or_h(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = cli.command_profile(
                type(
                    "Args",
                    (),
                    {"repository": ROOT, "output_dir": Path(directory), "force": False},
                )()
            )
            profiles = [json.loads(Path(path).read_text()) for path in result["outputs"]]
        self.assertEqual(result["profile_count"], 6)
        self.assertTrue(result["profiles_ready"])
        self.assertTrue(result["endpoint_qualification_passed"])
        self.assertTrue(result["matched_training_contract_frozen"])
        for profile in profiles:
            coordinates = {coordinate["name"] for coordinate in profile["coordinates"]}
            self.assertEqual(coordinates, set(cli.load_exporter(ROOT).COORDINATES))
            self.assertNotIn("usable_signal_density", coordinates)
            self.assertNotIn("effective_coverage", coordinates)
            checks = {check["check_id"]: check for check in profile["qualification_checks"]}
            self.assertEqual(checks["oracle-infrastructure-valid"]["status"], "pass")
            self.assertEqual(checks["bank-confirmation"]["status"], "pass")
            self.assertEqual(checks["training-outcomes-sealed"]["status"], "pass")
            self.assertNotEqual(
                profile["attributes"]["construction_view_seed"],
                profile["attributes"]["confirmation_view_seed"],
            )
            self.assertFalse(profile["attributes"]["training_outcomes_opened"])

    def test_verify_is_deterministic_and_authorizes_the_next_gate(self) -> None:
        arguments = type("Args", (), {"repository": ROOT})()
        first = cli.command_verify(arguments)
        second = cli.command_verify(arguments)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "pass")
        self.assertTrue(first["bank_confirmation_passed"])
        self.assertTrue(first["endpoint_qualification_passed"])
        self.assertTrue(first["matched_training_contract_frozen"])
        self.assertTrue(first["development_training_authorized"])

    def test_acquisition_results_remain_separate_from_profiles(self) -> None:
        arguments = type("Args", (), {"repository": ROOT})()
        first = cli.command_acquisition_results(arguments)
        second = cli.command_acquisition_results(arguments)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "pass")
        self.assertFalse(first["profile_input"])
        self.assertEqual(first["panels"]["antibody"]["support"]["units"], 150)
        self.assertEqual(first["panels"]["protein"]["support"]["units"], 175)
        self.assertAlmostEqual(
            first["panels"]["protein"]["primary_result"]["mean_normalized_regret"],
            0.05586555465277441,
        )


@unittest.skipUnless(os.name == "posix", "executable-wrapper test requires POSIX")
class MolecularCliCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        if not BINARY.is_file():
            subprocess.run(
                ["cargo", "build", "--quiet", "-p", "anarres-cli"],
                cwd=ROOT,
                check=True,
            )

    def wrapper(self, directory: Path) -> Path:
        path = directory / "anarres-molecular"
        python_path = os.pathsep.join(str(item) for item in [SOURCE, *SHARED_SOURCES])
        path.write_text(
            "#!/bin/sh\n"
            f"export PYTHONPATH={shlex.quote(python_path)}\n"
            f'exec {shlex.quote(sys.executable)} -m anarres_molecular_adapter.cli "$@"\n',
            encoding="utf-8",
        )
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def run_cli(self, directory: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PATH"] = os.pathsep.join([str(directory), environment.get("PATH", "")])
        return subprocess.run(
            [str(BINARY), *arguments],
            cwd=directory,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_doctor_and_status_work_outside_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.wrapper(directory)
            doctor = self.run_cli(directory, "adapter", "doctor", "molecular", "--json")
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            report = json.loads(doctor.stdout)
            self.assertTrue(report["valid"])
            self.assertEqual(report["descriptor"]["name"], "molecular")

            status = self.run_cli(
                directory,
                "molecular",
                "status",
                "--repository",
                str(ROOT),
                "--json",
            )
            self.assertEqual(status.returncode, 0, status.stderr)
            result = json.loads(status.stdout)
            self.assertTrue(result["bank_confirmation_passed"])
            self.assertTrue(result["endpoint_qualification_passed"])
            self.assertTrue(result["matched_training_contract_frozen"])
            self.assertTrue(result["development_training_authorized"])

            acquisition = self.run_cli(
                directory,
                "molecular",
                "acquisition-results",
                "--repository",
                str(ROOT),
                "--json",
            )
            self.assertEqual(acquisition.returncode, 0, acquisition.stderr)
            acquisition_result = json.loads(acquisition.stdout)
            self.assertFalse(acquisition_result["profile_input"])
            self.assertEqual(acquisition_result["panels"]["protein"]["support"]["units"], 175)

    def test_init_inspect_and_qualify_route_to_molecular_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.wrapper(directory)
            source = directory / "molecular-environment"
            helper = MolecularCliTest(
                methodName="test_native_source_qualification_precedes_measurement"
            )
            digest = helper.create_native_source(source)

            initialized = self.run_cli(
                directory,
                "init",
                str(source),
                "--adapter",
                "molecular",
                "--revision",
                f"sha256:{digest}",
                "--license",
                "mixed-public-sources",
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)

            inspected = self.run_cli(directory, "inspect", str(source), "--json")
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            inspection = json.loads(inspected.stdout)
            self.assertTrue(inspection["qualification_ready"])
            self.assertTrue(inspection["probe_ready"])
            self.assertEqual(inspection["native_format"], "rxnflow-molecular-environment-v1")

            qualified = self.run_cli(directory, "qualify", str(source), "--json")
            self.assertEqual(qualified.returncode, 0, qualified.stderr)
            report = json.loads(qualified.stdout)
            self.assertEqual(report["target_id"], "Q07820")
            self.assertTrue(report["policy_probe_available"])


if __name__ == "__main__":
    unittest.main()
