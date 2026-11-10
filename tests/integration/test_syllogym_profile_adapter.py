import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "experiments/legal/environment-selection/scripts/export_environment_profiles.py"
SPEC = importlib.util.spec_from_file_location("syllogym_profile_adapter", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SylloGymProfileAdapterTest(unittest.TestCase):
    def export(self, output: Path) -> list[Path]:
        return MODULE.export_profiles(
            release_path=MODULE.DEFAULT_RELEASE,
            measurements_path=MODULE.DEFAULT_MEASUREMENTS,
            selector_path=MODULE.DEFAULT_SELECTOR,
            decision_path=MODULE.DEFAULT_DECISION,
            sources_path=MODULE.DEFAULT_SOURCES,
            output_dir=output,
        )

    def test_released_measurement_exports_three_ready_profiles(self) -> None:
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
            self.assertEqual(len(outputs), 3)
            profiles = [json.loads(path.read_text()) for path in outputs]
            self.assertEqual(
                {profile["attributes"]["candidate_id"] for profile in profiles},
                {
                    "published_depth_weighted_control",
                    "uniform_14_task_control",
                    "frozen_policy_response_allocation",
                },
            )
            for profile in profiles:
                Draft202012Validator(schema, registry=registry).validate(profile)
                self.assertTrue(profile["attributes"]["outcome_blind"])
                self.assertEqual(profile["attributes"]["component_attempts"], 3584)
                self.assertEqual(len(profile["artifacts"]), 4)
                artifacts = {
                    item["role"]: item["reference"]["sha256"] for item in profile["artifacts"]
                }
                self.assertEqual(
                    artifacts["native-measurements"],
                    "sha256:d32c12c46ba68f18ca44a0b3150f6de91f28edac86dfdb62ec214cbe903f2b55",
                )
                self.assertEqual(
                    artifacts["selector-freeze"],
                    "sha256:14c187e006bfb3fedb2a00614bb06a249b7d2f640dc3385046a0bc712f3794bc",
                )
                checks = {item["check_id"]: item for item in profile["qualification_checks"]}
                self.assertTrue(all(item["status"] == "pass" for item in checks.values()))
                values = {item["name"]: item["value"] for item in profile["coordinates"]}
                self.assertEqual(values["missingness_rate"], 0.0)
                self.assertGreater(values["mean_token_cost"], 0.0)
                self.assertGreater(values["effective_task_coverage"], 0.0)
                self.assertLessEqual(values["effective_task_coverage"], 1.0)

    def test_candidate_projection_matches_released_measurements(self) -> None:
        expected = {
            "frozen_policy_response_allocation": (0.60618025, 0.62709283, 938.75960751),
            "published_depth_weighted_control": (0.65875922, 0.58482432, 980.86735026),
            "uniform_14_task_control": (0.66386719, 0.57905276, 943.84740940),
        }
        with tempfile.TemporaryDirectory() as directory:
            for path in self.export(Path(directory)):
                profile = json.loads(path.read_text())
                candidate = profile["attributes"]["candidate_id"]
                values = {item["name"]: item["value"] for item in profile["coordinates"]}
                readiness, entropy, cost = expected[candidate]
                self.assertAlmostEqual(values["readiness_fraction"], readiness, places=8)
                self.assertAlmostEqual(values["binary_reward_entropy_nats"], entropy, places=8)
                self.assertAlmostEqual(values["mean_token_cost"], cost, places=8)

    def test_profile_input_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            left = self.export(Path(first))
            right = self.export(Path(second))
            self.assertEqual([path.name for path in left], [path.name for path in right])
            self.assertEqual([digest(path) for path in left], [digest(path) for path in right])

    def test_tampered_measurement_is_rejected_by_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            measurements = json.loads(MODULE.DEFAULT_MEASUREMENTS.read_text())
            measurements["tasks"][0]["readiness"] = 0.0
            modified = temporary / "measurements.json"
            modified.write_text(json.dumps(measurements))
            with self.assertRaisesRegex(MODULE.AdapterError, "digest mismatch"):
                MODULE.export_profiles(
                    release_path=MODULE.DEFAULT_RELEASE,
                    measurements_path=modified,
                    selector_path=MODULE.DEFAULT_SELECTOR,
                    decision_path=MODULE.DEFAULT_DECISION,
                    sources_path=MODULE.DEFAULT_SOURCES,
                    output_dir=temporary / "profiles",
                )

    def test_source_revision_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            release = json.loads(MODULE.DEFAULT_RELEASE.read_text())
            release["source"]["revision"] = "different"
            modified = temporary / "release.json"
            modified.write_text(json.dumps(release))
            with self.assertRaisesRegex(MODULE.AdapterError, "source pin differs"):
                MODULE.export_profiles(
                    release_path=modified,
                    measurements_path=MODULE.DEFAULT_MEASUREMENTS,
                    selector_path=MODULE.DEFAULT_SELECTOR,
                    decision_path=MODULE.DEFAULT_DECISION,
                    sources_path=MODULE.DEFAULT_SOURCES,
                    output_dir=temporary / "profiles",
                )

    def test_incomplete_component_measurement_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            measurements = json.loads(MODULE.DEFAULT_MEASUREMENTS.read_text())
            measurements["tasks"].pop()
            modified_measurements = temporary / "measurements.json"
            modified_measurements.write_text(json.dumps(measurements))
            release = json.loads(MODULE.DEFAULT_RELEASE.read_text())
            release["native_artifacts"]["pretraining-task-measurements.json"] = digest(
                modified_measurements
            )
            modified_release = temporary / "release.json"
            modified_release.write_text(json.dumps(release))
            with self.assertRaisesRegex(MODULE.AdapterError, "incomplete generator support"):
                MODULE.export_profiles(
                    release_path=modified_release,
                    measurements_path=modified_measurements,
                    selector_path=MODULE.DEFAULT_SELECTOR,
                    decision_path=MODULE.DEFAULT_DECISION,
                    sources_path=MODULE.DEFAULT_SOURCES,
                    output_dir=temporary / "profiles",
                )

    def test_failed_reliability_is_not_converted_to_reward_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            measurements = json.loads(MODULE.DEFAULT_MEASUREMENTS.read_text())
            measurements["tasks"][0]["reliability_gate"] = False
            measurements["tasks"][0]["readiness"] = 0.0
            modified_measurements = temporary / "measurements.json"
            modified_measurements.write_text(json.dumps(measurements))
            release = json.loads(MODULE.DEFAULT_RELEASE.read_text())
            release["native_artifacts"]["pretraining-task-measurements.json"] = digest(
                modified_measurements
            )
            modified_release = temporary / "release.json"
            modified_release.write_text(json.dumps(release))
            with self.assertRaisesRegex(MODULE.AdapterError, "reliability gate"):
                MODULE.export_profiles(
                    release_path=modified_release,
                    measurements_path=modified_measurements,
                    selector_path=MODULE.DEFAULT_SELECTOR,
                    decision_path=MODULE.DEFAULT_DECISION,
                    sources_path=MODULE.DEFAULT_SOURCES,
                    output_dir=temporary / "profiles",
                )

    def test_outcomes_are_not_adapter_inputs(self) -> None:
        source = SCRIPT.read_text()
        self.assertNotIn("outcomes.json", source)
        self.assertNotIn("DEFAULT_OUTCOMES", source)

    def test_existing_profiles_are_not_silently_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            self.export(output)
            with self.assertRaises(FileExistsError):
                self.export(output)


if __name__ == "__main__":
    unittest.main()
