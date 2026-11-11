import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import h5py
from anarres_robotics_adapter import cli as CLI
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "experiments/robotics/environment-selection/prospective-cupid-can-v141"
SCRIPT = STUDY / "export_environment_profiles.py"
SPEC = importlib.util.spec_from_file_location("robotics_cupid_profile_adapter", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


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
        self.assertEqual(descriptor["version"], "0.5.0")
        self.assertEqual(descriptor["executable"], "anarres-robotics")
        self.assertEqual(descriptor["capabilities"], sorted(set(descriptor["capabilities"])))
        self.assertEqual(
            descriptor["measurement_contracts"],
            ["robotics.cupid-can-v141-candidate-measurement.v1"],
        )
        self.assertEqual(descriptor["source_formats"], ["robomimic-can-v141-hdf5"])

    def test_native_source_qualification_uses_manifest_and_dataset_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "can.hdf5"
            with h5py.File(dataset, "w") as handle:
                handle.create_group("data").create_group("demo_0")
            digest = hashlib.sha256(dataset.read_bytes()).hexdigest()
            manifest = root / "anarres.toml"
            manifest.write_text(
                "\n".join(
                    [
                        'schema_version = "anarres.environment-source.v1"',
                        'environment_id = "can-fixture"',
                        'domain = "robotics"',
                        'adapter = "robotics"',
                        'adapter_version = "0.5.0"',
                        'native_format = "robomimic-can-v141-hdf5"',
                        "",
                        "[source]",
                        'uri = "."',
                        f'revision = "sha256:{digest}"',
                        'license = "fixture-only"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            arguments = type("Args", (), {"manifest": manifest})()
            with mock.patch.object(CLI.workflow, "SOURCE_DATASET_SHA256", digest):
                report = CLI.command_qualify_source(arguments)
        self.assertEqual(report["status"], "qualified")
        self.assertEqual(report["demonstrations"], 1)
        self.assertFalse(report["policy_probe_available"])
        self.assertFalse(report["training_started"])

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
            self.assertTrue(report["candidate_outcomes_opened"])
            self.assertTrue(report["prospective_result_scored"])
            self.assertFalse(report["selector_superiority_established"])
            self.assertEqual(report["prospective_state"], "complete")
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
            self.assertEqual(plan["inputs"][0]["role"], "frozen_candidates")
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
            self.assertTrue(verification["candidate_outcomes_opened"])
            self.assertTrue(verification["released_result_recomputed"])

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

            can_results = self.run_adapter(
                ["can-results", "--repository", str(ROOT), "--json"], outside
            )
            self.assertEqual(can_results.returncode, 0, can_results.stderr)
            can_result = json.loads(can_results.stdout)
            self.assertEqual(can_result["frozen_prediction"], "cupid_tier_balanced_50")
            self.assertEqual(can_result["observed_best"], ["length_50"])
            self.assertAlmostEqual(can_result["allocation_regret_pp"], 1.4)
            self.assertIn("shortest-data baseline", can_result["claim_boundary"])
            self.assertTrue(
                all(value.startswith("sha256:") for value in can_result["artifacts"].values())
            )

    def test_frozen_candidates_are_complete_and_prepare_writes_every_mask(self) -> None:
        candidates_path = STUDY / "CANDIDATES.json"
        self.assertEqual(
            hashlib.sha256(candidates_path.read_bytes()).hexdigest(),
            "3b3b34e544dd5a1ce0740fb534a7fb0f5213f89173e657e6889b9e9e16ff5c8f",
        )
        frozen = CLI.workflow.read_candidates(candidates_path)
        self.assertEqual(set(frozen["candidates"]), {"all_data", *CLI.workflow.MASK_KEYS})
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = temporary / "source.hdf5"
            output = temporary / "prepared.hdf5"
            import h5py

            with h5py.File(source, "w") as dataset:
                data = dataset.create_group("data")
                for index in range(300):
                    data.create_group(f"demo_{index}")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            with mock.patch.object(CLI.workflow, "SOURCE_DATASET_SHA256", digest):
                report = CLI.workflow.prepare_dataset(source, output, candidates_path)
                self.assertFalse(report["candidate_outcomes_opened"])
                CLI.workflow.validate_prepared_dataset(output, candidates_path)
            with h5py.File(output, "r") as dataset:
                self.assertEqual(set(dataset["mask"]), set(CLI.workflow.MASK_KEYS.values()))
                for candidate_id, mask_key in CLI.workflow.MASK_KEYS.items():
                    self.assertEqual(
                        len(dataset["mask"][mask_key]),
                        frozen["candidates"][candidate_id]["count"],
                    )

    def test_run_task_requires_explicit_execution(self) -> None:
        with self.assertRaisesRegex(CLI.workflow.WorkflowError, "requires --execute"):
            CLI.workflow.run_task(Path("unused"), 0, "train", False)
        with self.assertRaisesRegex(CLI.workflow.WorkflowError, "requires --execute"):
            CLI.workflow.submit_bundle(Path("unused"), False)

    def test_bundle_binds_exact_tasks_without_starting_execution(self) -> None:
        candidates_path = STUDY / "CANDIDATES.json"
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = temporary / "source.hdf5"
            prepared = temporary / "prepared.hdf5"
            curaeval = temporary / "curaeval"
            (curaeval / "scripts").mkdir(parents=True)
            (curaeval / "scripts/run_dp.py").write_text("# fixture\n")
            import h5py

            with h5py.File(source, "w") as dataset:
                data = dataset.create_group("data")
                for index in range(300):
                    data.create_group(f"demo_{index}")
            source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
            runtime = {
                "executable": sys.executable,
                "python": sys.version,
                "platform": "fixture",
                "host_platform": "fixture",
                "missing_modules": [],
                "packages": ["fixture==1"],
                "packages_sha256": hashlib.sha256(b"fixture==1\n").hexdigest(),
            }
            plan = CLI.build_workflow_plan(ROOT)
            plan_path = temporary / "plan.json"
            plan_path.write_text(json.dumps(plan))
            bundle = temporary / "bundle"
            with (
                mock.patch.object(CLI.workflow, "SOURCE_DATASET_SHA256", source_digest),
                mock.patch.object(CLI.workflow, "validate_curaeval_checkout"),
                mock.patch.object(CLI.workflow, "runtime_fingerprint", return_value=runtime),
            ):
                CLI.workflow.prepare_dataset(source, prepared, candidates_path)
                report = CLI.workflow.write_bundle(
                    plan_path,
                    prepared,
                    candidates_path,
                    curaeval,
                    bundle,
                    sys.executable,
                    "slurm",
                    4,
                    "NVIDIA A40",
                    [],
                )
                local_bundle = temporary / "local-bundle"
                CLI.workflow.write_bundle(
                    plan_path,
                    prepared,
                    candidates_path,
                    curaeval,
                    local_bundle,
                    sys.executable,
                    "local",
                    2,
                    "NVIDIA A40",
                    [0, 2],
                )
            self.assertFalse(report["execution_started"])
            self.assertEqual(report["task_count"], 25)
            self.assertEqual(
                json.loads((bundle / "BUNDLE.json").read_text())["accelerator_name"],
                "NVIDIA A40",
            )
            tasks = [json.loads(line) for line in (bundle / "tasks.jsonl").read_text().splitlines()]
            self.assertEqual(len(tasks), 25)
            by_candidate = {task["candidate_id"]: task for task in tasks}
            self.assertEqual(by_candidate["all_data"]["filter_key"], "none")
            rollout_index = by_candidate["all_data"]["train_argv"].index("--rollout_n")
            self.assertEqual(by_candidate["all_data"]["train_argv"][rollout_index + 1], "0")
            self.assertEqual(
                by_candidate["cupid_tier_balanced_50"]["filter_key"],
                "anarres_cupid_tier_balanced_50",
            )
            launcher = (bundle / "submit-slurm.sh").read_text()
            self.assertIn("--dependency=afterok:$TRAIN", launcher)
            self.assertIn("--array=0-24%4", launcher)
            local_launcher = (local_bundle / "run-local.sh").read_text()
            self.assertIn("for gpu in 0 2", local_launcher)
            self.assertIn("expected='NVIDIA A40'", local_launcher)
            self.assertIn('observed=$(nvidia-smi --id="$gpu" --query-gpu=name', local_launcher)
            self.assertIn('if [ "$observed" != "$expected" ]', local_launcher)
            self.assertIn(
                'running=$(nvidia-smi --id="$gpu" --query-compute-apps=pid', local_launcher
            )
            self.assertIn('CUDA_VISIBLE_DEVICES="$gpu"', local_launcher)
            self.assertIn("run_phase train", local_launcher)
            self.assertIn("run_phase evaluate", local_launcher)
            fake_bin = temporary / "fake-bin"
            fake_bin.mkdir()
            fake_smi = fake_bin / "nvidia-smi"
            fake_smi.write_text(
                "#!/bin/sh\n"
                "[ \"$1\" = '--id=0' ] || exit 9\n"
                "[ \"$2\" = '--query-gpu=name' ] && echo 'NVIDIA A40'\n"
                "exit 0\n"
            )
            fake_smi.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = str(fake_bin)
            unavailable = subprocess.run(
                [str(local_bundle / "run-local.sh")],
                cwd=local_bundle,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(unavailable.returncode, 43)
            self.assertIn("gpu 2 is unavailable", unavailable.stderr)
            tasks_path = bundle / "tasks.jsonl"
            original_tasks = tasks_path.read_text()
            tasks_path.write_text(original_tasks.replace('"seed": 1', '"seed": 999', 1))
            with self.assertRaisesRegex(CLI.workflow.WorkflowError, "bound tasks artifact differs"):
                CLI.workflow.validate_bundle(bundle)

    def test_accelerator_check_uses_the_bound_python_runtime(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='["NVIDIA A40"]\n', stderr=""
        )
        with mock.patch.object(CLI.workflow.subprocess, "run", return_value=completed) as run:
            self.assertEqual(CLI.workflow.visible_accelerators("/runtime/python"), ["NVIDIA A40"])
        command = run.call_args.args[0]
        self.assertEqual(command[0], "/runtime/python")
        self.assertIn("torch.cuda.get_device_name", command[2])

    def test_release_gate_precedes_prospective_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)
            plan = CLI.build_workflow_plan(ROOT)
            tasks = CLI.workflow.task_records(
                plan,
                bundle / "prepared.hdf5",
                bundle / "CuraEval",
                bundle,
                sys.executable,
            )
            plan_path = bundle / "PLAN.json"
            runtime_path = bundle / "RUNTIME.json"
            tasks_path = bundle / "tasks.jsonl"
            launcher_path = bundle / "run-local.sh"
            dataset_path = bundle / "prepared.hdf5"
            plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
            runtime_path.write_text("{}\n")
            runtime_digest = f"sha256:{CLI.workflow.file_sha256(runtime_path)}"
            tasks_path.write_text("".join(json.dumps(task) + "\n" for task in tasks))
            launcher_path.write_text("#!/bin/sh\nexit 0\n")
            dataset_path.write_bytes(b"fixture")
            provenance = {
                "schema_version": "anarres.robotics-execution-bundle.v1",
                "plan_digest": plan["plan_digest"],
                "backend": "local",
                "task_count": len(tasks),
                "dataset": str(dataset_path),
                "dataset_sha256": f"sha256:{CLI.workflow.file_sha256(dataset_path)}",
                "curaeval": str(bundle / "CuraEval"),
                "python_executable": sys.executable,
                "candidate_freeze_sha256": next(
                    item["digest"] for item in plan["inputs"] if item["role"] == "frozen_candidates"
                ),
                "runtime_sha256": runtime_digest,
                "accelerator_name": "NVIDIA A40",
                "gpu_indices": [0],
                "frozen_point_prediction": "cupid_tier_balanced_50",
                "expected_evaluation_episodes": 2500,
                "bound_files": {
                    "plan": f"sha256:{CLI.workflow.file_sha256(plan_path)}",
                    "runtime": f"sha256:{CLI.workflow.file_sha256(runtime_path)}",
                    "tasks": f"sha256:{CLI.workflow.file_sha256(tasks_path)}",
                    "launcher": f"sha256:{CLI.workflow.file_sha256(launcher_path)}",
                },
            }
            provenance["bundle_digest"] = f"sha256:{CLI.workflow.object_sha256(provenance)}"
            (bundle / "BUNDLE.json").write_text(json.dumps(provenance))
            candidate_rates = {
                "all_data": 0.50,
                "random_50": 0.45,
                "length_50": 0.55,
                "cupid_50": 0.60,
                "cupid_tier_balanced_50": 0.65,
            }
            for task in tasks:
                run_root = Path(task["run_root"])
                checkpoint = run_root / "training/models/last.pth"
                checkpoint.parent.mkdir(parents=True)
                checkpoint.write_bytes(task["run_id"].encode())
                checkpoint_digest = f"sha256:{CLI.workflow.file_sha256(checkpoint)}"
                logs = {
                    "TRAIN_COMPLETE.json": (run_root / "train.log", "training complete\n"),
                    "EVALUATION_COMPLETE.json": (
                        run_root / "evaluation.log",
                        "Average Rollout Stats\n"
                        + json.dumps(
                            {
                                "Success_Rate": candidate_rates[task["candidate_id"]],
                                "Horizon": 400,
                            }
                        )
                        + "\n",
                    ),
                }
                for record_name, (log_path, content) in logs.items():
                    log_path.write_text(content)
                    stage = "train" if record_name.startswith("TRAIN") else "evaluate"
                    record = {
                        "plan_digest": plan["plan_digest"],
                        "run_id": task["run_id"],
                        "stage": stage,
                        "runtime_sha256": runtime_digest,
                        "accelerator_name": "NVIDIA A40",
                        "task_sha256": f"sha256:{CLI.workflow.object_sha256(task)}",
                        "log_sha256": f"sha256:{CLI.workflow.file_sha256(log_path)}",
                        "checkpoint_sha256": checkpoint_digest,
                    }
                    argv = (
                        task["train_argv"]
                        if stage == "train"
                        else CLI.workflow.evaluation_argv(task, checkpoint)
                    )
                    record["command_sha256"] = f"sha256:{CLI.workflow.argv_sha256(argv)}"
                    if stage == "evaluate":
                        record["evaluation_episodes"] = task["evaluation_episodes"]
                    (run_root / record_name).write_text(json.dumps(record))
            with self.assertRaisesRegex(CLI.workflow.WorkflowError, "requires a passing"):
                CLI.workflow.score_bundle(bundle)
            gate = CLI.workflow.release_gate(bundle)
            self.assertFalse(gate["candidate_outcomes_opened"])
            result = CLI.workflow.score_bundle(bundle)
            self.assertTrue(result["candidate_outcomes_opened"])
            self.assertTrue(result["prediction_is_observed_best"])
            self.assertEqual(result["allocation_regret_pp"], 0.0)
            self.assertEqual(result["observed_best"], ["cupid_tier_balanced_50"])

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
