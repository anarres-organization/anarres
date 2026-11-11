import tempfile
import unittest
from pathlib import Path

from anarres.core import SourceManifestError, load_source_manifest


class SourceManifestTest(unittest.TestCase):
    def write_manifest(self, root: Path, **replacements: str) -> Path:
        values = {
            "adapter": "robotics",
            "adapter_version": "0.5.0",
            "domain": "robotics",
            "native_format": "robomimic-hdf5",
        }
        values.update(replacements)
        manifest = root / "anarres.toml"
        manifest.write_text(
            "\n".join(
                [
                    'schema_version = "anarres.environment-source.v1"',
                    'environment_id = "can-v141"',
                    f'adapter = "{values["adapter"]}"',
                    f'adapter_version = "{values["adapter_version"]}"',
                    f'domain = "{values["domain"]}"',
                    f'native_format = "{values["native_format"]}"',
                    "",
                    "[source]",
                    'uri = "."',
                    'revision = "sha256:fixture"',
                    'license = "Apache-2.0"',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return manifest

    def test_local_source_is_bound_to_adapter_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = load_source_manifest(
                self.write_manifest(root),
                expected_adapter="robotics",
                expected_version="0.5.0",
                expected_domain="robotics",
                accepted_formats=("robomimic-hdf5",),
            )
        self.assertEqual(source.environment_id, "can-v141")
        self.assertEqual(source.source, root.resolve())

    def test_adapter_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.write_manifest(Path(directory), adapter="legal")
            with self.assertRaisesRegex(SourceManifestError, "does not match"):
                load_source_manifest(
                    manifest,
                    expected_adapter="robotics",
                    expected_version="0.5.0",
                    expected_domain="robotics",
                    accepted_formats=("robomimic-hdf5",),
                )


if __name__ == "__main__":
    unittest.main()
