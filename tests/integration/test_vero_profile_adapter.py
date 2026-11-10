import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "data/formal-verification/vero/export_environment_profiles.py"
SPEC = importlib.util.spec_from_file_location("vero_profile_adapter", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class VeroProfileAdapterTest(unittest.TestCase):
    def export(self, output: Path) -> list[Path]:
        return MODULE.export_profiles(
            result_path=MODULE.DEFAULT_RESULT,
            protocol_path=MODULE.DEFAULT_PROTOCOL,
            source_pin_path=MODULE.DEFAULT_SOURCE_PIN,
            output_dir=output,
        )

    def test_released_negative_measurement_exports_two_unready_profiles(self) -> None:
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
            self.assertEqual(len(outputs), 2)
            profiles = [json.loads(path.read_text()) for path in outputs]
            self.assertEqual(
                {profile["attributes"]["mode"] for profile in profiles}, {"proof", "codeproof"}
            )
            for profile in profiles:
                Draft202012Validator(schema, registry=registry).validate(profile)
                checks = {check["check_id"]: check for check in profile["qualification_checks"]}
                self.assertEqual(checks["infrastructure-valid"]["status"], "pass")
                self.assertEqual(checks["preregistered-support"]["status"], "fail")
                values = {item["name"]: item["value"] for item in profile["coordinates"]}
                self.assertEqual(values["usable_signal_density"], 0.0)
                self.assertEqual(values["effective_verification_coverage"], 0.0)
                self.assertGreater(values["mean_model_tokens_per_attempt"], 0.0)
                self.assertEqual(len(profile["artifacts"]), 3)
                artifact_digests = {
                    artifact["role"]: artifact["reference"]["sha256"]
                    for artifact in profile["artifacts"]
                }
                self.assertEqual(
                    artifact_digests,
                    {
                        "measurement-contract": (
                            "sha256:ea3f696bb3b60da0d217d303d80bd5447be919014b8850fb9bd83a7441f99bf0"
                        ),
                        "native-measurements": (
                            "sha256:8c93cf6b1c345906bfcb83d3af6850f5b8717d303ed9bd33065efb60444ea3cb"
                        ),
                        "source-pin": (
                            "sha256:670361cdebb1d9d77d1dcd51b4e754734c8d4357dbb1291700ef97f9dca8850e"
                        ),
                    },
                )

    def test_export_is_byte_stable_for_released_evidence(self) -> None:
        expected = {
            "vero-development-codeproof-v5.profile-input.json": (
                "2df8fe89418f98ee6a4de4fa266dbea16c980143fd1cf89fe7b92c64cb85c4c1"
            ),
            "vero-development-proof-v5.profile-input.json": (
                "cbf4283bd32c754a45e3b50e8a6b323623ff54eb94555f40ace8d6d26da4de10"
            ),
        }
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_outputs = self.export(Path(first))
            second_outputs = self.export(Path(second))
            self.assertEqual(
                {path.name: path.read_bytes() for path in first_outputs},
                {path.name: path.read_bytes() for path in second_outputs},
            )
            self.assertEqual(
                {
                    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in first_outputs
                },
                expected,
            )

    def test_frozen_protocol_digest_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            protocol = json.loads(MODULE.DEFAULT_PROTOCOL.read_text())
            protocol["starting_policy"]["temperature"] = 0.5
            modified = temporary / "protocol.json"
            modified.write_text(json.dumps(protocol))
            with self.assertRaisesRegex(MODULE.AdapterError, "does not match"):
                MODULE.export_profiles(
                    result_path=MODULE.DEFAULT_RESULT,
                    protocol_path=modified,
                    source_pin_path=MODULE.DEFAULT_SOURCE_PIN,
                    output_dir=temporary / "profiles",
                )

    def test_missing_source_revision_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = json.loads(MODULE.DEFAULT_SOURCE_PIN.read_text())
            source["commit"] = ""
            modified = temporary / "source-pin.json"
            modified.write_text(json.dumps(source))
            with self.assertRaisesRegex(MODULE.AdapterError, "nonempty commit"):
                MODULE.export_profiles(
                    result_path=MODULE.DEFAULT_RESULT,
                    protocol_path=MODULE.DEFAULT_PROTOCOL,
                    source_pin_path=modified,
                    output_dir=temporary / "profiles",
                )

    def test_infrastructure_failure_is_not_exported_as_reward_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            result = json.loads(MODULE.DEFAULT_RESULT.read_text())
            result["execution"]["infrastructure_valid_attempts"] = 31
            result["execution"]["infrastructure_errors"] = 1
            modified = temporary / "result.json"
            modified.write_text(json.dumps(result))
            with self.assertRaisesRegex(MODULE.AdapterError, "infrastructure-valid"):
                MODULE.export_profiles(
                    result_path=modified,
                    protocol_path=MODULE.DEFAULT_PROTOCOL,
                    source_pin_path=MODULE.DEFAULT_SOURCE_PIN,
                    output_dir=temporary / "profiles",
                )

    def test_missing_native_measurement_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            result = json.loads(MODULE.DEFAULT_RESULT.read_text())
            del result["measurement"]["by_mode"]["proof"]["effective_coverage_H"]
            modified = temporary / "result.json"
            modified.write_text(json.dumps(result))
            with self.assertRaisesRegex(MODULE.AdapterError, "nonfinite coordinate"):
                MODULE.export_profiles(
                    result_path=modified,
                    protocol_path=MODULE.DEFAULT_PROTOCOL,
                    source_pin_path=MODULE.DEFAULT_SOURCE_PIN,
                    output_dir=temporary / "profiles",
                )

    def test_existing_profile_is_not_silently_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            self.export(output)
            with self.assertRaises(FileExistsError):
                self.export(output)


if __name__ == "__main__":
    unittest.main()
