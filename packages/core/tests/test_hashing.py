import unittest

from anarres.core import ArtifactReference, sha256_digest


class HashingTest(unittest.TestCase):
    def test_digest_is_order_independent(self) -> None:
        self.assertEqual(sha256_digest({"a": 1, "b": 2}), sha256_digest({"b": 2, "a": 1}))

    def test_artifact_requires_prefixed_digest(self) -> None:
        with self.assertRaises(ValueError):
            ArtifactReference(
                uri="hf://datasets/example",
                sha256="bad",
                media_type="application/json",
                size_bytes=1,
                license="Apache-2.0",
            )


if __name__ == "__main__":
    unittest.main()
