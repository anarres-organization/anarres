import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
STUDY = (
    ROOT / "experiments" / "ai-for-science" / "molecular-design" / "reaction-environment-selection"
)
SCRIPT = STUDY / "scripts" / "export_environment_profiles.py"
SPEC = importlib.util.spec_from_file_location("molecular_profile_adapter", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
EXPECTED_NATIVE_SHA256 = {
    "BANK_CONFIRMATION_SCORING_AUDIT_V2.json": (
        "3438114210d7390a2aa88c6636d5b36bec89396e7becd309fced186ef85993dc"
    ),
    "BANK_CONSTRUCTION_CONTRACT_V3.json": (
        "bdc4a8099fb370cd4dfbd7b8f6f3a0abdff8552c01f3b8ea00a74afb6b004d9d"
    ),
    "BANK_CONSTRUCTION_CONTRACT_V4.json": (
        "ecc979116c8843853a4f972bff736ab03bda903e8164e81e82cd4af86f799625"
    ),
    "DEVELOPMENT_BANK_QUALIFICATION_AUDIT_V1.json": (
        "05cf438a5c776956046937594206bfa480a485e72bd290198e645894378e8abe"
    ),
    "DEVELOPMENT_BANK_QUALIFICATION_V3.json": (
        "c8ed1d3b578444125e7b2307e668695e0073d264bd60588ac20673ffb49a85a4"
    ),
    "DEVELOPMENT_BANK_QUALIFICATION_V4.json": (
        "50792a7c66a6e6e43c680c163e70df11bf8e77a7f8af6638905d5cf3ed7b26c0"
    ),
    "MEASUREMENT_CONTRACT_V4.json": (
        "f4245a141ca9fa794f5b93b6d10cd25298ece2fa4b2d3090b6862c8b18fa5693"
    ),
    "MEASUREMENT_RELIABILITY_RESULT_V3.json": (
        "9201752e2ce5a50c6c49cd37db970defcbde1609081149edec8d5244d6298d7a"
    ),
    "MOLGENBENCH_ARCHIVE_AUDIT.json": (
        "66f0c99870f95171504e06936cbe4924f4c62f46232350fd04707d4b6e057145"
    ),
    "ORACLE_QUALIFICATION.json": "73b50d61d804584de1440c1a4fe32c1c3f4d6018577ebcc906fe74fa38209e54",
    "PROTOCOL.json": "c1e71f46717dad9056482460f1dbda30defad09b2699997961214069ec1b8936",
    "SOURCE_AUDIT.json": "251de1707b7d8dae01d531ae3b6d969a1fb305137684852f8aa71a474aaa3ec4",
    "TARGET_FIXTURE_AUDIT.json": "cd229c4c2439af24823316623635f8217be7fb376881b41470fd3e5cd2dfa3b5",
    "TARGET_REWARD_CONTRACT_V3.json": (
        "b0c6ecd62d70783edb0c2daa1705f6bf06810af4fd9f04a091d7af9bb10c145d"
    ),
    "TARGET_SELECTION_RESULT.json": (
        "5a3eb10b7b506c6eec6f30b8a090492555c64d9a63c7dd6f3b0322bbd62362a3"
    ),
    "WARM_START_QUALIFICATION.json": (
        "319c44211b55113e1b4adebfbf470296a34b03ef40c3ffe2e2a5dd04fa71813e"
    ),
}


class MolecularProfileAdapterTest(unittest.TestCase):
    def test_frozen_native_artifact_digests(self) -> None:
        observed = {name: MODULE.sha256(STUDY / name) for name in EXPECTED_NATIVE_SHA256}
        self.assertEqual(observed, EXPECTED_NATIVE_SHA256)

    def native_inputs(self) -> list[dict]:
        result = json.loads((STUDY / "DEVELOPMENT_BANK_QUALIFICATION_V4.json").read_text())
        paths = [
            "DEVELOPMENT_BANK_QUALIFICATION_V3.json",
            "MEASUREMENT_RELIABILITY_RESULT_V3.json",
            "MEASUREMENT_CONTRACT_V4.json",
            "BANK_CONSTRUCTION_CONTRACT_V4.json",
            "WARM_START_QUALIFICATION.json",
            "TARGET_SELECTION_RESULT.json",
            "SOURCE_AUDIT.json",
            "MOLGENBENCH_ARCHIVE_AUDIT.json",
            "TARGET_FIXTURE_AUDIT.json",
            "ORACLE_QUALIFICATION.json",
            "TARGET_REWARD_CONTRACT_V3.json",
            "DEVELOPMENT_BANK_QUALIFICATION_AUDIT_V1.json",
            "BANK_CONFIRMATION_SCORING_AUDIT_V2.json",
            "PROTOCOL.json",
        ]
        return [result, *[json.loads((STUDY / path).read_text()) for path in paths]]

    def write_native_result(self, directory: Path, *, zero_reward: bool = False) -> Path:
        result = self.native_inputs()[0]
        if zero_reward:
            for bank in result["summaries"][0].values():
                bank["mean_target_reward"] = 0.0
        path = directory / "DEVELOPMENT_BANK_QUALIFICATION_V4.json"
        path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return path

    def profile_validator(self) -> Draft202012Validator:
        schemas = [
            json.loads(path.read_text()) for path in sorted((ROOT / "schemas").rglob("*.json"))
        ]
        registry = Registry()
        for schema in schemas:
            if isinstance(schema.get("$id"), str):
                registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
        profile_schema = next(
            schema
            for schema in schemas
            if schema.get("$id", "").endswith("environment-profile-input.v1.schema.json")
        )
        return Draft202012Validator(profile_schema, registry=registry)

    def test_non_authorizing_v1_bank_result_is_rejected(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(MODULE.AdapterError, "scored version 4"),
        ):
            MODULE.export_profiles(
                result_path=STUDY / "DEVELOPMENT_BANK_QUALIFICATION_V1.json",
                output_dir=Path(directory),
            )

    def test_missing_native_bank_result_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            with self.assertRaisesRegex(MODULE.AdapterError, "does not exist"):
                MODULE.export_profiles(result_path=missing, output_dir=Path(directory) / "out")

    def test_archive_fixture_revision_mismatch_is_rejected(self) -> None:
        inputs = self.native_inputs()
        inputs[9] = copy.deepcopy(inputs[9])
        inputs[9]["archive_sha256"] = "0" * 64
        with self.assertRaisesRegex(MODULE.AdapterError, "not bound to the audited archive"):
            MODULE.validate_inputs(*inputs)

    def test_opened_training_outcomes_are_rejected(self) -> None:
        inputs = self.native_inputs()
        inputs[-1] = copy.deepcopy(inputs[-1])
        inputs[-1]["sealed_boundary"]["training_or_evaluation_outcomes_inspected"] = True
        with self.assertRaisesRegex(MODULE.AdapterError, "outcomes are not sealed"):
            MODULE.validate_inputs(*inputs)

    def test_missing_source_revision_is_rejected(self) -> None:
        inputs = self.native_inputs()
        inputs[7] = copy.deepcopy(inputs[7])
        inputs[7]["rxnflow"].pop("commit")
        with self.assertRaisesRegex(MODULE.AdapterError, "source revision is absent"):
            MODULE.validate_inputs(*inputs)

    def test_oracle_infrastructure_failure_is_not_converted_to_reward_zero(self) -> None:
        inputs = self.native_inputs()
        inputs[2] = copy.deepcopy(inputs[2])
        inputs[2]["views"][0]["oracle_completion_fraction"] = 0.999
        with self.assertRaisesRegex(MODULE.AdapterError, "infrastructure-invalid oracle"):
            MODULE.validate_inputs(*inputs)

    def test_selected_target_requires_qualified_oracle_record(self) -> None:
        inputs = self.native_inputs()
        inputs[10] = copy.deepcopy(inputs[10])
        inputs[10]["targets"] = [
            item for item in inputs[10]["targets"] if item["target_id"] != "Q07820"
        ]
        with self.assertRaisesRegex(MODULE.AdapterError, "qualified oracle panel"):
            MODULE.validate_inputs(*inputs)

    def test_native_bundle_exports_six_deterministic_schema_valid_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            result = self.write_native_result(temporary)
            first = MODULE.export_profiles(result_path=result, output_dir=temporary / "first")
            second = MODULE.export_profiles(result_path=result, output_dir=temporary / "second")
            self.assertEqual(len(first), 6)
            self.assertEqual(
                [path.read_bytes() for path in first], [path.read_bytes() for path in second]
            )
            validator = self.profile_validator()
            for path in first:
                profile = json.loads(path.read_text())
                validator.validate(profile)
                self.assertEqual(profile["domain"], "molecular-design")
                self.assertEqual(profile["measurement_contract"]["repetitions"], 2)
                self.assertEqual(len(profile["coordinates"]), 8)
                self.assertEqual(len(profile["artifacts"]), 15)
                checks = {check["check_id"]: check for check in profile["qualification_checks"]}
                self.assertTrue(all(check["status"] == "pass" for check in checks.values()))
                self.assertTrue(profile["attributes"]["bank_confirmation_passed"])
                self.assertEqual(profile["attributes"]["confirmation_rule"], "selector_fidelity")
                self.assertEqual(profile["attributes"]["failed_confirmation_checks"], "")
                self.assertFalse(profile["attributes"]["predictive_evidence_available"])

    def test_scientific_zero_is_preserved_as_a_coordinate_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            result = self.write_native_result(temporary, zero_reward=True)
            outputs = MODULE.export_profiles(result_path=result, output_dir=temporary / "profiles")
            for path in outputs:
                profile = json.loads(path.read_text())
                values = {
                    coordinate["name"]: coordinate["value"] for coordinate in profile["coordinates"]
                }
                self.assertEqual(values["mean_target_reward"], 0.0)

    def test_negative_native_measurement_is_rejected(self) -> None:
        inputs = self.native_inputs()
        inputs[0] = copy.deepcopy(inputs[0])
        inputs[0]["summaries"][0]["hash_uniform"]["mean_target_reward"] = -0.1
        with self.assertRaisesRegex(MODULE.AdapterError, "finite and nonnegative"):
            MODULE.validate_inputs(*inputs)

    def test_existing_profile_is_not_silently_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            result = self.write_native_result(temporary)
            output = temporary / "profiles"
            MODULE.export_profiles(result_path=result, output_dir=output)
            with self.assertRaises(FileExistsError):
                MODULE.export_profiles(result_path=result, output_dir=output)


if __name__ == "__main__":
    unittest.main()
