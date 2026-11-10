import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "experiments/ai-for-science/materials-science/mlip-phonon-environment-selection"
SCRIPT = STUDY / "export_environment_profiles.py"
SPEC = importlib.util.spec_from_file_location("materials_mlip_profile_adapter", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

CANDIDATES = [
    "aimd-from-PBE-1000-npt__hash_uniform",
    "aimd-from-PBE-1000-npt__low_signal",
]
EXPECTED_PROFILE_DIGESTS = {
    "aimd-from-PBE-1000-npt__hash_uniform": (
        "sha256:498ae6352e2f4ef3d377da58f5ce59e3fae3bd11cdf1b3ea415a4eefc31f8660",
        "sha256:4ddee981ba1de131278f49cddc2fc0f86d337d6e7035b90041887f378c830bb7",
    ),
    "aimd-from-PBE-1000-npt__low_signal": (
        "sha256:9ad790cbf55446ae727a60cfb13eba7cde90e4c3e306702e07f22afbabd6c394",
        "sha256:0c606858d190d86f11a81740f1874ffb39a433daf1b8a4f67167a838168a3b69",
    ),
}


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
                self.assertEqual(checks["final-panel-pending"]["status"], "unknown")
                self.assertEqual(checks["final-panel-pending"]["severity"], "warning")
                self.assertEqual(len(payload["artifacts"]), 7)
                self.assertNotIn("uncertainty", payload["coordinates"][0])

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
                    "8eb317d7e363db79a35cf3fd04cbb30a18d4a8a40b548619596235ce38e2edf6",
                    "450ae4bec5c1986fbea392d1edee03e3a1ece0fa8bad0a25f2c2d2470b0f31f8",
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


if __name__ == "__main__":
    unittest.main()
