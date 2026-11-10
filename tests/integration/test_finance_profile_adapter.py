import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "experiments/finance/environment-selection/export_environment_profile.py"
SPEC = importlib.util.spec_from_file_location("finance_profile_adapter", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

EXPECTED_ARTIFACT_DIGESTS = {
    "QWEN3_8B_QUALIFICATION.json": (
        "8682b31039d12b3feb85d2750d85b8f24f6ed2e17b99e25111fc65b2b3467569"
    ),
    "PROTOCOL.json": "5807321e94ced65939ac4a3cebe46f3a5e8351f5eaef7a24a64cbb5203a9b3f5",
    "PREFLIGHT.json": "fe7c4c065b7f601fd2281d42c0a6b12e33ee77d0e68562ab333180a6a8fa1c08",
    "SOURCES.json": "18c6c5fda2d466f3d909bf5f20b023c630f1ca0af0460e9891a05d00badbeede",
    "business_bench_openai_policy.py": (
        "0fac00379af601fe29077bda368bad0ad4f4845b75464335b07804a05b55bf62"
    ),
}
EXPECTED_PROFILE_INPUT_SHA256 = "3b606ff1107b0b41976fb3e87467ba144c9e66ba46de4e5d3ba7dac5b0e8c4dc"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FinanceProfileAdapterTest(unittest.TestCase):
    def export(self, output: Path) -> Path:
        return MODULE.export_profile(
            result_path=MODULE.DEFAULT_RESULT,
            protocol_path=MODULE.DEFAULT_PROTOCOL,
            preflight_path=MODULE.DEFAULT_PREFLIGHT,
            sources_path=MODULE.DEFAULT_SOURCES,
            harness_path=MODULE.DEFAULT_HARNESS,
            output_dir=output,
        )

    def test_released_failure_exports_one_unready_profile(self) -> None:
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
            output = self.export(Path(directory))
            profile = json.loads(output.read_text())
        Draft202012Validator(schema, registry=registry).validate(profile)

        self.assertEqual(profile["domain"], "agentic-finance")
        self.assertEqual(profile["subject"]["revision"], MODULE.MODEL_REVISION)
        self.assertFalse(profile["attributes"]["qualified"])
        self.assertEqual(profile["attributes"]["infrastructure_failures"], 3)

        values = {item["name"]: item for item in profile["coordinates"]}
        self.assertEqual(values["executable_completion_rate"]["value"], 0.0)
        self.assertEqual(values["executable_completion_rate"]["sample_count"], 74)
        self.assertEqual(values["mixed_scenario_group_fraction"]["value"], 0.0)
        self.assertEqual(values["mixed_scenario_group_fraction"]["sample_count"], 4)
        self.assertEqual(values["truncation_rate"]["value"], 0.992)
        self.assertEqual(values["median_generated_tokens_per_episode"]["value"], 8192.0)
        self.assertEqual(values["median_tool_calls_per_episode"]["unit"], "tool_calls_per_episode")

        checks = {item["check_id"]: item for item in profile["qualification_checks"]}
        self.assertEqual(checks["planned-episode-accounting"]["status"], "pass")
        self.assertEqual(checks["infrastructure-failures-present"]["status"], "fail")
        self.assertEqual(checks["infrastructure-failures-present"]["severity"], "warning")
        self.assertEqual(checks["truncation-rate-at-most-0-10"]["status"], "fail")
        self.assertEqual(len(profile["artifacts"]), 5)

    def test_native_artifact_digests_are_exact(self) -> None:
        paths = [
            MODULE.DEFAULT_RESULT,
            MODULE.DEFAULT_PROTOCOL,
            MODULE.DEFAULT_PREFLIGHT,
            MODULE.DEFAULT_SOURCES,
            MODULE.DEFAULT_HARNESS,
        ]
        for path in paths:
            self.assertEqual(sha256(path), EXPECTED_ARTIFACT_DIGESTS[path.name])

    def test_export_is_byte_deterministic_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_output = self.export(Path(first))
            second_output = self.export(Path(second))
            self.assertEqual(first_output.read_bytes(), second_output.read_bytes())
            self.assertEqual(sha256(first_output), EXPECTED_PROFILE_INPUT_SHA256)
            with self.assertRaises(FileExistsError):
                self.export(Path(first))

    def test_missing_measurement_and_source_revision_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            result = json.loads(MODULE.DEFAULT_RESULT.read_text())
            del result["truncation_rate"]
            result_path = temporary / "result.json"
            result_path.write_text(json.dumps(result))
            with self.assertRaisesRegex(MODULE.AdapterError, "truncation_rate"):
                MODULE.export_profile(
                    result_path=result_path,
                    protocol_path=MODULE.DEFAULT_PROTOCOL,
                    preflight_path=MODULE.DEFAULT_PREFLIGHT,
                    sources_path=MODULE.DEFAULT_SOURCES,
                    harness_path=MODULE.DEFAULT_HARNESS,
                    output_dir=temporary / "missing-measurement",
                )

            sources = json.loads(MODULE.DEFAULT_SOURCES.read_text())
            for source in sources["sources"]:
                if source["id"] == "business_bench":
                    del source["revision"]
            sources_path = temporary / "sources.json"
            sources_path.write_text(json.dumps(sources))
            with self.assertRaisesRegex(MODULE.AdapterError, "revision is missing"):
                MODULE.export_profile(
                    result_path=MODULE.DEFAULT_RESULT,
                    protocol_path=MODULE.DEFAULT_PROTOCOL,
                    preflight_path=MODULE.DEFAULT_PREFLIGHT,
                    sources_path=sources_path,
                    harness_path=MODULE.DEFAULT_HARNESS,
                    output_dir=temporary / "missing-revision",
                )

    def test_downstream_outcomes_are_not_adapter_inputs(self) -> None:
        source = SCRIPT.read_text()
        self.assertNotIn("retrospective-post-training", source)
        self.assertNotIn("OUTCOMES.json", source)
        self.assertNotIn("SCORE.json", source)


if __name__ == "__main__":
    unittest.main()
