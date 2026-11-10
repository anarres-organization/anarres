import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import h5py

ROOT = Path(__file__).parent


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PREPARE = load("square_prepare_candidates", ROOT / "scripts/prepare_candidate_dataset.py")


class CandidateExecutionTest(unittest.TestCase):
    def test_prepared_masks_are_bound_to_frozen_memberships(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.hdf5"
            with h5py.File(source, "w") as dataset:
                data = dataset.create_group("data")
                for index in range(6):
                    data.create_group(f"demo_{index}")
            protocol = {
                "study_id": "square-test",
                "source": {"dataset_sha256": PREPARE.sha256(source)},
                "candidates": [
                    {"id": "all_data_reference"},
                    {"id": "candidate_a"},
                ],
            }
            protocol_path = root / "protocol.json"
            protocol_path.write_text(json.dumps(protocol))
            members = ["demo_0", "demo_2", "demo_4"]
            candidates = {
                "study_id": "square-test",
                "status": "CANDIDATES_AND_PREDICTIONS_FROZEN__CANDIDATE_OUTCOMES_UNOPENED",
                "candidate_outcomes_opened": False,
                "candidates": {
                    "all_data_reference": {
                        "count": 6,
                        "members": [f"demo_{index}" for index in range(6)],
                        "membership_sha256": PREPARE.hashlib.sha256(
                            "".join(f"demo_{index}\n" for index in range(6)).encode()
                        ).hexdigest(),
                    },
                    "candidate_a": {
                        "count": 3,
                        "members": members,
                        "membership_sha256": PREPARE.hashlib.sha256(
                            b"demo_0\ndemo_2\ndemo_4\n"
                        ).hexdigest(),
                    },
                },
            }
            candidates_path = root / "candidates.json"
            candidates_path.write_text(json.dumps(candidates))
            prepared = root / "prepared.hdf5"
            report = PREPARE.prepare(source, prepared, candidates_path, protocol_path)
            self.assertFalse(report["candidate_outcomes_opened"])
            with h5py.File(prepared, "r") as dataset:
                observed = [
                    value.decode() for value in dataset["mask"][PREPARE.mask_key("candidate_a")][:]
                ]
            self.assertEqual(observed, members)

            prepared.chmod(0o644)
            with h5py.File(prepared, "a") as dataset:
                del dataset["mask"][PREPARE.mask_key("candidate_a")]
                dataset["mask"].create_dataset(
                    PREPARE.mask_key("candidate_a"), data=[b"demo_1", b"demo_3", b"demo_5"]
                )
            with self.assertRaisesRegex(ValueError, "prepared mask mismatch"):
                PREPARE.validate_prepared(prepared, candidates_path, protocol_path)


if __name__ == "__main__":
    unittest.main()
