#!/usr/bin/env python3

import importlib.util
import json
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "convert_business_bench_qualification.py"
SPEC = importlib.util.spec_from_file_location("convert_business_bench_qualification", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write_attempt(root: Path, exit_code: int = 0) -> Path:
    attempt = root / "task__policy__s1__r1"
    out = attempt / "turns" / "1" / "out"
    out.mkdir(parents=True)
    (out / "anarres_policy_trace.json").write_text(
        json.dumps(
            {
                "episode_seed": 17,
                "protocol_valid": True,
                "truncated": False,
                "usage": {"completion_tokens": 123},
                "events": [{"tool_results": [{"name": "erp"}]}],
            }
        )
    )
    result = {
        "task": "payment-run",
        "seed": 1,
        "run": 1,
        "passed": True,
        "breach": False,
        "error": None,
        "turns": [{"n": 1, "exit_code": exit_code, "timed_out": False}],
    }
    path = attempt / "result.json"
    path.write_text(json.dumps(result))
    return path


def test_valid_attempt_conversion() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        path = write_attempt(Path(temporary))
        row = MODULE.load_attempt(path, "qwen3-8b")
    assert row["infrastructure_valid"] is True
    assert row["tool_protocol_valid"] is True
    assert row["reward"] == 1.0
    assert row["generated_tokens"] == 123
    assert row["tool_calls"] == 1
    assert row["rollout_seed"] == 17


def test_nonzero_harness_exit_is_infrastructure_failure() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        path = write_attempt(Path(temporary), exit_code=1)
        row = MODULE.load_attempt(path, "qwen3-8b")
    assert row["infrastructure_valid"] is False
    assert row["reward"] == 0.0
    assert row["tool_protocol_valid"] is False


if __name__ == "__main__":
    test_valid_attempt_conversion()
    test_nonzero_harness_exit_is_infrastructure_failure()
