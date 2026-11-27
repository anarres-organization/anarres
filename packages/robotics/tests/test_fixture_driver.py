import shutil
import tempfile
import unittest
from pathlib import Path

from anarres.core import load_source_manifest
from anarres.robotics.contract import RoboticsContractError
from anarres.robotics.drivers.base import installed_formats, load_driver

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "fixture-source"


def load_fixture(root: Path):
    return load_source_manifest(
        root / "anarres.toml",
        expected_adapter="robotics",
        expected_version="0.6.0",
        expected_domain="robotics",
        accepted_formats=tuple(installed_formats()),
    )


class FixtureDriverTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp())
        self.root = self.directory / "source"
        shutil.copytree(FIXTURE, self.root)
        self.driver = load_driver("robotics-fixture-v1")

    def tearDown(self) -> None:
        shutil.rmtree(self.directory)

    def test_describes_native_source(self) -> None:
        description = self.driver.describe(load_fixture(self.root))
        self.assertEqual(description.episodes, 4)
        self.assertEqual(description.episode_unit.grouping_key, "initial_state_id")
        self.assertEqual(description.cost_fields, {"control_steps": "step"})
        self.assertIn("language_instruction", description.missing)
        self.assertEqual(description.content_digest, description.revision)

    def test_description_is_deterministic(self) -> None:
        source = load_fixture(self.root)
        self.assertEqual(
            self.driver.describe(source).to_record(), self.driver.describe(source).to_record()
        )
        self.assertEqual(self.driver.tasks(source), self.driver.tasks(source))

    def test_tampered_episodes_are_rejected(self) -> None:
        with (self.root / "episodes.jsonl").open("a", encoding="utf-8") as handle:
            handle.write("\n")
        with self.assertRaisesRegex(RoboticsContractError, "revision"):
            self.driver.describe(load_fixture(self.root))

    def test_missing_contract_field_is_rejected(self) -> None:
        (self.root / "contract.json").write_text('{"seeds": [0]}\n', encoding="utf-8")
        with self.assertRaisesRegex(RoboticsContractError, "evaluation contract is missing"):
            self.driver.describe(load_fixture(self.root))

    def test_unknown_format_is_rejected(self) -> None:
        with self.assertRaisesRegex(RoboticsContractError, "no installed driver"):
            load_driver("libero-hdf5")


if __name__ == "__main__":
    unittest.main()
