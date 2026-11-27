import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from anarres_coding_adapter import cli
from anarres_coding_adapter.marin import MarinEvidenceError, audit_fixed_validation
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[4]


class CodingCliTest(unittest.TestCase):
    def write_marin_csv(self, path: Path, *, inconsistent: bool = False) -> str:
        columns = (
            "dataset",
            "recipe",
            "job",
            "attempt",
            "step",
            "pass_at_1",
            "passes",
            "total",
            "avg_score",
            "split_seed",
            "split_revision",
            "contaminated",
            "status",
        )
        rows = [
            (
                "BugsInPy",
                "recipe-a",
                "/job/a",
                0,
                0,
                0.5 if not inconsistent else 0.4,
                2,
                4,
                0.4,
                42,
                "split-a",
                "false",
                "authoritative",
            ),
            (
                "BugsInPy",
                "recipe-b",
                "/job/b",
                0,
                0,
                0.25,
                1,
                4,
                0.2,
                42,
                "split-a",
                "false",
                "authoritative_policy_stop",
            ),
            (
                "SWE-Gym",
                "recipe-c",
                "/job/c",
                0,
                0,
                0.75,
                3,
                4,
                0.7,
                42,
                "split-b",
                "false",
                "authoritative",
            ),
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(columns)
            writer.writerows(rows)
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_descriptor_is_valid_and_side_effect_free(self) -> None:
        descriptor = cli.adapter_descriptor()
        schema = json.loads(
            (ROOT / "schemas/adapters/adapter-descriptor.v1.schema.json").read_text()
        )
        Draft202012Validator(schema).validate(descriptor)
        self.assertEqual(descriptor["name"], "coding")
        self.assertEqual(descriptor["capabilities"], sorted(descriptor["capabilities"]))
        self.assertEqual(descriptor["source_formats"], [])

    def test_status_reports_decisions_regressions_and_boundaries(self) -> None:
        result = cli.command_status(type("Args", (), {"repository": ROOT})())
        self.assertEqual(result["independent_exact_decisions"], 2)
        self.assertEqual(result["exact_best_candidate_decisions"], 3)
        self.assertEqual(result["bridge_sources"], 7)
        self.assertEqual(result["regression_held_out_repositories"], 22)
        self.assertFalse(result["native_policy_probe_available"])

    def test_profile_exports_released_and_external_measurements(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = type(
                "Args",
                (),
                {"repository": ROOT, "output": Path(directory), "panel": "all"},
            )()
            result = cli.command_profile(args)
            self.assertGreater(result["panels"]["released"]["profiles"], 0)
            self.assertGreater(result["panels"]["external"]["profiles"], 0)
            self.assertTrue(list(Path(directory).glob("*.profile-input.json")))
            self.assertFalse((Path(directory) / "released").exists())

    def test_profile_accepts_shared_output_directory_option(self) -> None:
        arguments = cli.parser().parse_args(["profile", "--output-dir", "/tmp/profiles"])
        self.assertEqual(arguments.output, Path("/tmp/profiles"))

    def test_marin_audit_qualifies_within_dataset_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "software-transfer-fixed-validation.csv"
            digest = self.write_marin_csv(path)
            result = audit_fixed_validation(
                path,
                expected_sha256=digest,
                source_revision="gist:example",
                source_license="public artifact; upstream terms apply",
            )
        self.assertEqual(result["status"], "qualified_evidence_record")
        self.assertTrue(result["datasets"]["BugsInPy"]["within_dataset_comparison_qualified"])
        self.assertFalse(result["datasets"]["SWE-Gym"]["within_dataset_comparison_qualified"])
        self.assertFalse(result["cross_dataset_allocation_comparable"])
        self.assertFalse(result["policy_probe_available"])

    def test_marin_audit_rejects_bad_accounting_and_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "software-transfer-fixed-validation.csv"
            digest = self.write_marin_csv(path, inconsistent=True)
            with self.assertRaisesRegex(MarinEvidenceError, "passes / total"):
                audit_fixed_validation(
                    path,
                    expected_sha256=digest,
                    source_revision="gist:example",
                    source_license="public artifact",
                )
            with self.assertRaisesRegex(MarinEvidenceError, "digest mismatch"):
                audit_fixed_validation(
                    path,
                    expected_sha256="0" * 64,
                    source_revision="gist:example",
                    source_license="public artifact",
                )


if __name__ == "__main__":
    unittest.main()
