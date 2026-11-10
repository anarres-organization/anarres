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

    def test_existing_profile_is_not_silently_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            self.export(output)
            with self.assertRaises(FileExistsError):
                self.export(output)


if __name__ == "__main__":
    unittest.main()
