#!/usr/bin/env python3

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "score_policy_qualification.py"
SPEC = importlib.util.spec_from_file_location("score_policy_qualification", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def make_rows() -> list[dict]:
    rows = []
    for workflow_index in range(4):
        for scenario_index in range(2):
            for rollout in range(4):
                reward = int(workflow_index < 2 and scenario_index == 0 and rollout == 0)
                rows.append(
                    {
                        "policy_id": "fixture-policy",
                        "workflow": f"workflow-{workflow_index}",
                        "scenario_id": f"scenario-{scenario_index}",
                        "rollout_seed": rollout,
                        "infrastructure_valid": True,
                        "tool_protocol_valid": True,
                        "reward": reward,
                        "material_control_violation": False,
                        "generated_tokens": 1000 + rollout,
                        "tool_calls": 4 + rollout,
                        "truncated": False,
                    }
                )
    return rows


def test_qualifying_record() -> None:
    summary = MODULE.score(make_rows(), 4, 2, 4)
    assert summary["recorded_episodes"] == 32
    assert summary["mixed_scenario_groups"] == 2
    assert summary["workflows_with_mixed_groups"] == ["workflow-0", "workflow-1"]
    assert summary["qualified"] is True


def test_infrastructure_failure_is_not_reward_zero() -> None:
    rows = make_rows()
    rows[0]["infrastructure_valid"] = False
    rows[0]["reward"] = 0
    summary = MODULE.score(rows, 4, 2, 4)
    assert summary["infrastructure_failures"] == 1
    assert summary["valid_episodes"] == 31
    assert summary["complete_scenario_groups"] == 7
    assert summary["qualified"] is False


def test_duplicate_identity_is_rejected() -> None:
    rows = make_rows()
    rows.append(dict(rows[0]))
    try:
        MODULE.score(rows, 4, 2, 4)
    except ValueError as error:
        assert "duplicate episode identities" in str(error)
    else:
        raise AssertionError("duplicate identity was accepted")


def test_excessive_truncation_fails_qualification() -> None:
    rows = make_rows()
    for row in rows[:4]:
        row["truncated"] = True
    summary = MODULE.score(rows, 4, 2, 4)
    assert summary["truncation_rate"] == 0.125
    assert summary["gates"]["truncation_rate_at_most_0_10"] is False
    assert summary["qualified"] is False


if __name__ == "__main__":
    test_qualifying_record()
    test_infrastructure_failure_is_not_reward_zero()
    test_duplicate_identity_is_rejected()
    test_excessive_truncation_fails_qualification()
