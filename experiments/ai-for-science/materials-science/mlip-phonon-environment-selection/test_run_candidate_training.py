import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).with_name("run_candidate_training.py")
SPEC = importlib.util.spec_from_file_location("run_candidate_training", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def contract(tmp_path, status="frozen_before_final_candidate_training"):
    path = tmp_path / "contract.json"
    path.write_text(
        json.dumps(
            {
                "status": status,
                "environments": {
                    "development": [{"candidate_id": "a"}, {"candidate_id": "b"}],
                    "prospective": [{"candidate_id": "c"}],
                },
                "randomization": {"training_seeds": [0, 1]},
            }
        ),
        encoding="utf-8",
    )
    return path


def test_workers_partition_complete_development_matrix(tmp_path):
    path = contract(tmp_path)
    shards = [MODULE.tasks(path, "development", index, 3) for index in range(3)]
    flattened = [(task["candidate_id"], task["seed"]) for shard in shards for task in shard]
    assert sorted(flattened) == [("a", 0), ("a", 1), ("b", 0), ("b", 1)]


def test_prospective_training_is_blocked_before_forecast(tmp_path):
    with pytest.raises(ValueError, match="predictions are frozen"):
        MODULE.tasks(contract(tmp_path), "prospective", 0, 1)
