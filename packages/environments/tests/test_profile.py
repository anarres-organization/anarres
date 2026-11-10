import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from anarres.environments.profile import (
    MissingEvidenceError,
    build_profile_input,
    coordinate,
    local_artifact,
    qualification_check,
    write_profile_input,
)
from jsonschema import Draft202012Validator


class EnvironmentProfileAdapterTest(unittest.TestCase):
    def profile(self) -> dict:
        return build_profile_input(
            environment_id="robotics-fixture-a",
            domain="robotics",
            subject={"kind": "policy", "id": "policy-a", "revision": "weights-1"},
            producer={"kind": "adapter", "id": "robotics.fixture", "revision": "1"},
            source={"uri": "fixture://episodes", "revision": "1", "license": "CC0-1.0"},
            measurement_contract={
                "kind": "episode-probe",
                "id": "robotics.fixture.v1",
                "revision": "1",
                "repetitions": 3,
                "cost_unit": "action_steps",
            },
            qualification_checks=[
                qualification_check(
                    check_id="runtime",
                    category="infrastructure",
                    status="pass",
                    severity="error",
                    summary="Fixture runtime completed.",
                )
            ],
            coordinates=[
                coordinate(
                    name="policy_weakness",
                    definition_uri="https://example.org/robotics/policy-weakness",
                    definition_revision="1",
                    role="robotics.policy_frontier",
                    value=0.4,
                    unit="fraction",
                    direction="contextual",
                    estimator="episode mean",
                    sample_count=30,
                )
            ],
        )

    def test_native_artifact_preserves_exact_digest_and_size(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "native.json"
            source.write_bytes(b'{"native":true}\n')
            artifact = local_artifact(
                role="native-measurements",
                path=source,
                uri="release://native.json",
                media_type="application/json",
                license_id="Apache-2.0",
            )
            self.assertEqual(
                artifact["reference"]["sha256"],
                f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}",
            )
            self.assertEqual(artifact["reference"]["size_bytes"], len(source.read_bytes()))

    def test_missing_native_artifact_is_not_converted_to_missing_measurement(self) -> None:
        with self.assertRaises(MissingEvidenceError):
            local_artifact(
                role="native-measurements",
                path=Path("does-not-exist.json"),
                uri="release://missing.json",
                media_type="application/json",
                license_id="Apache-2.0",
            )

    def test_profile_requires_measured_coordinates(self) -> None:
        with self.assertRaisesRegex(MissingEvidenceError, "do not infer them from outcomes"):
            build_profile_input(
                environment_id="legal-a",
                domain="legal",
                subject={"kind": "policy", "id": "policy-a", "revision": "1"},
                producer={"kind": "adapter", "id": "legal.fixture", "revision": "1"},
                source={"uri": "fixture://legal", "revision": "1", "license": "CC0-1.0"},
                measurement_contract={"kind": "probe", "id": "p", "revision": "1"},
                qualification_checks=[{"status": "pass"}],
                coordinates=[],
            )

    def test_atomic_writer_is_deterministic_and_refuses_clobber(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "profile.json"
            profile = self.profile()
            write_profile_input(output, profile)
            expected = json.dumps(profile, indent=2, sort_keys=True, allow_nan=False) + "\n"
            self.assertEqual(output.read_text(encoding="utf-8"), expected)
            with self.assertRaises(FileExistsError):
                write_profile_input(output, profile)
            write_profile_input(output, profile, force=True)
            self.assertEqual(output.read_text(encoding="utf-8"), expected)

    def test_builder_output_conforms_to_public_schema(self) -> None:
        root = Path(__file__).resolve().parents[3]
        schema_path = root / "schemas/environments/environment-profile-input.v1.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(self.profile())


if __name__ == "__main__":
    unittest.main()
