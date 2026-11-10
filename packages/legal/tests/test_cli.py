import json
import tempfile
import unittest
from pathlib import Path

from anarres.legal import cli

ROOT = Path(__file__).resolve().parents[3]


class LegalCliTest(unittest.TestCase):
    def test_descriptor_is_sorted_and_side_effect_free(self) -> None:
        descriptor = cli.adapter_descriptor()
        self.assertEqual(descriptor["schema_version"], "anarres.adapter-descriptor.v1")
        self.assertEqual(descriptor["name"], "legal")
        self.assertEqual(descriptor["executable"], "anarres-legal")
        self.assertEqual(descriptor["capabilities"], sorted(set(descriptor["capabilities"])))

    def test_status_separates_syllogym_from_lab(self) -> None:
        args = type("Args", (), {"repository": ROOT})()
        result = cli.command_status(args)
        self.assertFalse(result["syllogym"]["candidate_training_outcomes_used_by_adapter"])
        self.assertEqual(result["lab"]["role"], "separate_task_regression_evaluation")
        self.assertFalse(result["lab"]["profile_input"])

    def test_profile_reuses_outcome_blind_exporter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            args = type(
                "Args",
                (),
                {
                    "repository": ROOT,
                    "output_dir": Path(directory),
                    "force": False,
                },
            )()
            result = cli.command_profile(args)
            profiles = [json.loads(Path(path).read_text()) for path in result["outputs"]]
        self.assertEqual(result["profile_count"], 3)
        self.assertFalse(result["outcomes_artifact_read"])
        self.assertTrue(all(profile["attributes"]["outcome_blind"] for profile in profiles))
        self.assertTrue(
            all(
                "usable_signal_density"
                not in {coordinate["name"] for coordinate in profile["coordinates"]}
                for profile in profiles
            )
        )

    def test_verify_is_byte_deterministic(self) -> None:
        args = type("Args", (), {"repository": ROOT})()
        first = cli.command_verify(args)
        second = cli.command_verify(args)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "pass")
        self.assertFalse(first["outcomes_artifact_read"])

    def test_explicit_repository_supports_execution_outside_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                import os

                os.chdir(directory)
                result = cli.command_status(type("Args", (), {"repository": ROOT})())
            finally:
                os.chdir(previous)
        self.assertEqual(result["domain"], "legal-reasoning")


if __name__ == "__main__":
    unittest.main()
