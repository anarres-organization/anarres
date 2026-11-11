"""Validate and content-address a portable Harvey LAB execution contract."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "anarres.legal-lab-execution-contract.v1"
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET_KEYS = {
    "access_token",
    "api_key",
    "credential",
    "password",
    "secret",
}
_REQUIRED_INVALID_CONDITIONS = {
    "contract_mismatch",
    "document_conversion_failure",
    "judge_outage",
    "missing_judge_score",
    "missing_metrics",
    "model_outage",
    "run_not_finished_cleanly",
    "sandbox_failure",
    "ungraded_criterion",
}


class LabExecutionContractError(ValueError):
    """Raised when a LAB execution contract is incomplete or inconsistent."""


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LabExecutionContractError(f"{field} must be an object")
    return value


def _exact_keys(value: dict[str, Any], field: str, required: set[str]) -> None:
    missing = sorted(required - set(value))
    extra = sorted(set(value) - required)
    if missing:
        raise LabExecutionContractError(f"{field} is missing required fields: {missing}")
    if extra:
        raise LabExecutionContractError(f"{field} has unsupported fields: {extra}")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LabExecutionContractError(f"{field} must be non-empty text")
    return value.strip()


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _text(value, field)


def _boolean(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise LabExecutionContractError(f"{field} must be true or false")
    return value


def _integer(value: Any, field: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise LabExecutionContractError(f"{field} must be an integer >= {minimum}")
    return value


def _number(value: Any, field: str, *, minimum: float = 0.0) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < minimum:
        raise LabExecutionContractError(f"{field} must be a number >= {minimum}")
    return float(value)


def _digest(value: Any, field: str) -> str:
    text = _text(value, field)
    if not _DIGEST.fullmatch(text):
        raise LabExecutionContractError(f"{field} must be a sha256:<64 lowercase hex> digest")
    return text


def _string_list(
    value: Any,
    field: str,
    *,
    minimum: int = 0,
    unique: bool = True,
) -> list[str]:
    if not isinstance(value, list) or len(value) < minimum:
        raise LabExecutionContractError(f"{field} must contain at least {minimum} item(s)")
    result = [_text(item, f"{field}[{index}]") for index, item in enumerate(value)]
    if unique and len(set(result)) != len(result):
        raise LabExecutionContractError(f"{field} must not contain duplicates")
    return result


def _reject_credentials(value: Any, field: str = "contract") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = key.lower().replace("-", "_")
            if normalized in _SECRET_KEYS:
                raise LabExecutionContractError(
                    f"{field}.{key} is credential material and must not be serialized"
                )
            _reject_credentials(item, f"{field}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_credentials(item, f"{field}[{index}]")
    elif isinstance(value, str):
        lowered = value.lower()
        if value.startswith("sk-") or "-----begin private key-----" in lowered:
            raise LabExecutionContractError(f"{field} appears to contain credential material")


def _validate_source(value: Any) -> dict[str, Any]:
    source = _object(value, "source")
    required = {"environment_id", "license", "revision", "task_set_sha256"}
    _exact_keys(source, "source", required)
    return {
        "environment_id": _text(source["environment_id"], "source.environment_id"),
        "license": _text(source["license"], "source.license"),
        "revision": _text(source["revision"], "source.revision"),
        "task_set_sha256": _digest(source["task_set_sha256"], "source.task_set_sha256"),
    }


def _validate_policy(value: Any) -> dict[str, Any]:
    policy = _object(value, "starting_policy_stage.policy")
    required = {"checkpoint_id", "checkpoint_revision", "model_id", "model_revision"}
    _exact_keys(policy, "starting_policy_stage.policy", required)
    return {
        "checkpoint_id": _text(
            policy["checkpoint_id"], "starting_policy_stage.policy.checkpoint_id"
        ),
        "checkpoint_revision": _text(
            policy["checkpoint_revision"],
            "starting_policy_stage.policy.checkpoint_revision",
        ),
        "model_id": _text(policy["model_id"], "starting_policy_stage.policy.model_id"),
        "model_revision": _text(
            policy["model_revision"], "starting_policy_stage.policy.model_revision"
        ),
    }


def _validate_compaction(value: Any) -> dict[str, Any]:
    compaction = _object(value, "starting_policy_stage.compaction")
    required = {
        "context_window_tokens",
        "implementation_revision",
        "strategy",
        "trigger_tokens",
    }
    _exact_keys(compaction, "starting_policy_stage.compaction", required)
    strategy = _text(compaction["strategy"], "starting_policy_stage.compaction.strategy")
    context_window = compaction["context_window_tokens"]
    trigger = compaction["trigger_tokens"]
    revision = compaction["implementation_revision"]
    if strategy == "none":
        if any(item is not None for item in (context_window, trigger, revision)):
            raise LabExecutionContractError(
                "compaction thresholds and revision must be null when strategy is none"
            )
        return {
            "context_window_tokens": None,
            "implementation_revision": None,
            "strategy": "none",
            "trigger_tokens": None,
        }
    context_window_value = _integer(
        context_window, "starting_policy_stage.compaction.context_window_tokens", minimum=1
    )
    trigger_value = _integer(trigger, "starting_policy_stage.compaction.trigger_tokens", minimum=1)
    if trigger_value > context_window_value:
        raise LabExecutionContractError("compaction trigger_tokens exceeds context_window_tokens")
    return {
        "context_window_tokens": context_window_value,
        "implementation_revision": _text(
            revision, "starting_policy_stage.compaction.implementation_revision"
        ),
        "strategy": strategy,
        "trigger_tokens": trigger_value,
    }


def _validate_starting_policy_stage(value: Any) -> dict[str, Any]:
    stage = _object(value, "starting_policy_stage")
    required = {
        "allowed_tools",
        "compaction",
        "document_access",
        "finish_tool_enabled",
        "harness",
        "max_turns",
        "policy",
        "reasoning_effort",
        "sandbox_image",
        "sandbox_image_digest",
        "shell_timeout_seconds",
        "skills",
        "system_prompt_sha256",
        "temperature",
    }
    _exact_keys(stage, "starting_policy_stage", required)
    harness = _object(stage["harness"], "starting_policy_stage.harness")
    _exact_keys(
        harness,
        "starting_policy_stage.harness",
        {"name", "package_sha256", "revision", "version"},
    )
    document_access = _object(stage["document_access"], "starting_policy_stage.document_access")
    _exact_keys(
        document_access,
        "starting_policy_stage.document_access",
        {"matter_documents", "network", "output"},
    )
    skills = stage["skills"]
    if not isinstance(skills, list):
        raise LabExecutionContractError("starting_policy_stage.skills must be a list")
    validated_skills: list[dict[str, str]] = []
    skill_ids: set[str] = set()
    for index, raw_skill in enumerate(skills):
        skill = _object(raw_skill, f"starting_policy_stage.skills[{index}]")
        _exact_keys(skill, f"starting_policy_stage.skills[{index}]", {"id", "sha256"})
        skill_id = _text(skill["id"], f"starting_policy_stage.skills[{index}].id")
        if skill_id in skill_ids:
            raise LabExecutionContractError(f"duplicate starting-policy skill: {skill_id}")
        skill_ids.add(skill_id)
        validated_skills.append(
            {
                "id": skill_id,
                "sha256": _digest(skill["sha256"], f"starting_policy_stage.skills[{index}].sha256"),
            }
        )
    return {
        "allowed_tools": _string_list(
            stage["allowed_tools"], "starting_policy_stage.allowed_tools", minimum=1
        ),
        "compaction": _validate_compaction(stage["compaction"]),
        "document_access": {
            "matter_documents": _text(
                document_access["matter_documents"],
                "starting_policy_stage.document_access.matter_documents",
            ),
            "network": _text(
                document_access["network"], "starting_policy_stage.document_access.network"
            ),
            "output": _text(
                document_access["output"], "starting_policy_stage.document_access.output"
            ),
        },
        "finish_tool_enabled": _boolean(
            stage["finish_tool_enabled"], "starting_policy_stage.finish_tool_enabled"
        ),
        "harness": {
            "name": _text(harness["name"], "starting_policy_stage.harness.name"),
            "package_sha256": _digest(
                harness["package_sha256"], "starting_policy_stage.harness.package_sha256"
            ),
            "revision": _text(harness["revision"], "starting_policy_stage.harness.revision"),
            "version": _text(harness["version"], "starting_policy_stage.harness.version"),
        },
        "max_turns": _integer(stage["max_turns"], "starting_policy_stage.max_turns", minimum=1),
        "policy": _validate_policy(stage["policy"]),
        "reasoning_effort": _optional_text(
            stage["reasoning_effort"], "starting_policy_stage.reasoning_effort"
        ),
        "sandbox_image": _text(stage["sandbox_image"], "starting_policy_stage.sandbox_image"),
        "sandbox_image_digest": _digest(
            stage["sandbox_image_digest"], "starting_policy_stage.sandbox_image_digest"
        ),
        "shell_timeout_seconds": _integer(
            stage["shell_timeout_seconds"],
            "starting_policy_stage.shell_timeout_seconds",
            minimum=1,
        ),
        "skills": sorted(validated_skills, key=lambda item: item["id"]),
        "system_prompt_sha256": _digest(
            stage["system_prompt_sha256"], "starting_policy_stage.system_prompt_sha256"
        ),
        "temperature": _number(stage["temperature"], "starting_policy_stage.temperature"),
    }


def _validate_judge_stage(value: Any) -> dict[str, Any]:
    stage = _object(value, "judge_stage")
    required = {
        "document_conversion",
        "grader_revision",
        "harness",
        "judge_profile",
        "judges",
        "parallel_calls",
        "retry",
        "rubric_prompt_sha256",
    }
    _exact_keys(stage, "judge_stage", required)
    harness = _object(stage["harness"], "judge_stage.harness")
    _exact_keys(
        harness,
        "judge_stage.harness",
        {"name", "package_sha256", "revision", "version"},
    )
    judges = stage["judges"]
    if not isinstance(judges, list) or not 1 <= len(judges) <= 2:
        raise LabExecutionContractError("judge_stage.judges must contain one or two judges")
    validated_judges: list[dict[str, str]] = []
    judge_ids: set[str] = set()
    for index, raw_judge in enumerate(judges):
        judge = _object(raw_judge, f"judge_stage.judges[{index}]")
        _exact_keys(judge, f"judge_stage.judges[{index}]", {"model_id", "model_revision"})
        model_id = _text(judge["model_id"], f"judge_stage.judges[{index}].model_id")
        if model_id in judge_ids:
            raise LabExecutionContractError(f"duplicate judge model: {model_id}")
        judge_ids.add(model_id)
        validated_judges.append(
            {
                "model_id": model_id,
                "model_revision": _text(
                    judge["model_revision"],
                    f"judge_stage.judges[{index}].model_revision",
                ),
            }
        )
    conversion = _object(stage["document_conversion"], "judge_stage.document_conversion")
    _exact_keys(
        conversion,
        "judge_stage.document_conversion",
        {"pandoc_version", "track_changes_mode"},
    )
    retry = _object(stage["retry"], "judge_stage.retry")
    _exact_keys(
        retry,
        "judge_stage.retry",
        {"backoff_seconds", "max_attempts", "retryable_conditions"},
    )
    return {
        "document_conversion": {
            "pandoc_version": _text(
                conversion["pandoc_version"],
                "judge_stage.document_conversion.pandoc_version",
            ),
            "track_changes_mode": _text(
                conversion["track_changes_mode"],
                "judge_stage.document_conversion.track_changes_mode",
            ),
        },
        "grader_revision": _text(stage["grader_revision"], "judge_stage.grader_revision"),
        "harness": {
            "name": _text(harness["name"], "judge_stage.harness.name"),
            "package_sha256": _digest(
                harness["package_sha256"], "judge_stage.harness.package_sha256"
            ),
            "revision": _text(harness["revision"], "judge_stage.harness.revision"),
            "version": _text(harness["version"], "judge_stage.harness.version"),
        },
        "judge_profile": _text(stage["judge_profile"], "judge_stage.judge_profile"),
        "judges": validated_judges,
        "parallel_calls": _integer(
            stage["parallel_calls"], "judge_stage.parallel_calls", minimum=1
        ),
        "retry": {
            "backoff_seconds": _number(
                retry["backoff_seconds"], "judge_stage.retry.backoff_seconds"
            ),
            "max_attempts": _integer(
                retry["max_attempts"], "judge_stage.retry.max_attempts", minimum=1
            ),
            "retryable_conditions": _string_list(
                retry["retryable_conditions"],
                "judge_stage.retry.retryable_conditions",
                minimum=1,
            ),
        },
        "rubric_prompt_sha256": _digest(
            stage["rubric_prompt_sha256"], "judge_stage.rubric_prompt_sha256"
        ),
    }


def _validate_outcome_semantics(value: Any) -> dict[str, Any]:
    semantics = _object(value, "outcome_semantics")
    required = {
        "all_pass",
        "criterion",
        "deliverable_completion",
        "headline",
    }
    _exact_keys(semantics, "outcome_semantics", required)
    if semantics["criterion"] != "binary_pass_fail":
        raise LabExecutionContractError("outcome_semantics.criterion must be binary_pass_fail")
    if semantics["all_pass"] != "every_criterion_passes_for_each_judge":
        raise LabExecutionContractError(
            "outcome_semantics.all_pass must require every criterion to pass for each judge"
        )
    if semantics["headline"] != "task_all_pass":
        raise LabExecutionContractError("outcome_semantics.headline must be task_all_pass")
    completion = _object(
        semantics["deliverable_completion"], "outcome_semantics.deliverable_completion"
    )
    _exact_keys(
        completion,
        "outcome_semantics.deliverable_completion",
        {"metric", "missing_required_deliverable"},
    )
    return {
        "all_pass": "every_criterion_passes_for_each_judge",
        "criterion": "binary_pass_fail",
        "deliverable_completion": {
            "metric": _text(
                completion["metric"], "outcome_semantics.deliverable_completion.metric"
            ),
            "missing_required_deliverable": _text(
                completion["missing_required_deliverable"],
                "outcome_semantics.deliverable_completion.missing_required_deliverable",
            ),
        },
        "headline": "task_all_pass",
    }


def _validate_accounting(value: Any) -> dict[str, Any]:
    accounting = _object(value, "accounting")
    required = {"currency", "metrics", "price_schedule_revision", "retry_accounting"}
    _exact_keys(accounting, "accounting", required)
    required_metrics = {
        "agent_input_tokens",
        "agent_output_tokens",
        "agent_wall_clock_seconds",
        "estimated_cost",
        "judge_calls",
        "judge_input_tokens",
        "judge_output_tokens",
        "judge_wall_clock_seconds",
        "retry_count",
    }
    metrics = set(_string_list(accounting["metrics"], "accounting.metrics", minimum=1))
    missing = sorted(required_metrics - metrics)
    if missing:
        raise LabExecutionContractError(
            f"accounting.metrics is missing required metrics: {missing}"
        )
    return {
        "currency": _text(accounting["currency"], "accounting.currency"),
        "metrics": sorted(metrics),
        "price_schedule_revision": _text(
            accounting["price_schedule_revision"], "accounting.price_schedule_revision"
        ),
        "retry_accounting": _text(accounting["retry_accounting"], "accounting.retry_accounting"),
    }


def _validate_target_scope(value: Any) -> dict[str, Any]:
    target = _object(value, "target_scope")
    required = {
        "diagnostics",
        "practice_areas",
        "protected_outcomes",
        "workflows",
    }
    _exact_keys(target, "target_scope", required)
    protected = _object(target["protected_outcomes"], "target_scope.protected_outcomes")
    _exact_keys(
        protected,
        "target_scope.protected_outcomes",
        {"available_before_freeze", "practice_areas", "workflow_outcomes"},
    )
    available = _boolean(
        protected["available_before_freeze"],
        "target_scope.protected_outcomes.available_before_freeze",
    )
    if available:
        raise LabExecutionContractError("protected outcomes must be unavailable before freeze")
    return {
        "diagnostics": _string_list(target["diagnostics"], "target_scope.diagnostics", minimum=1),
        "practice_areas": _string_list(
            target["practice_areas"], "target_scope.practice_areas", minimum=1
        ),
        "protected_outcomes": {
            "available_before_freeze": False,
            "practice_areas": _string_list(
                protected["practice_areas"],
                "target_scope.protected_outcomes.practice_areas",
            ),
            "workflow_outcomes": _string_list(
                protected["workflow_outcomes"],
                "target_scope.protected_outcomes.workflow_outcomes",
                minimum=1,
            ),
        },
        "workflows": _string_list(target["workflows"], "target_scope.workflows", minimum=1),
    }


def _validate_execution(value: Any) -> dict[str, Any]:
    execution = _object(value, "execution")
    required = {
        "credentials",
        "execution_started",
        "mode",
        "submission_requires_explicit_command",
    }
    _exact_keys(execution, "execution", required)
    if execution["mode"] != "contract_only":
        raise LabExecutionContractError("execution.mode must be contract_only")
    if execution["execution_started"] is not False:
        raise LabExecutionContractError("execution.execution_started must be false")
    if execution["submission_requires_explicit_command"] is not True:
        raise LabExecutionContractError(
            "execution.submission_requires_explicit_command must be true"
        )
    credentials = _object(execution["credentials"], "execution.credentials")
    _exact_keys(
        credentials,
        "execution.credentials",
        {"inherited_at_runtime", "serialized"},
    )
    if credentials["inherited_at_runtime"] is not True or credentials["serialized"] is not False:
        raise LabExecutionContractError(
            "credentials must be inherited at runtime and never serialized"
        )
    return {
        "credentials": {"inherited_at_runtime": True, "serialized": False},
        "execution_started": False,
        "mode": "contract_only",
        "submission_requires_explicit_command": True,
    }


def validate(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a normalized contract after strict structural validation."""

    _reject_credentials(raw)
    allowed = {
        "accounting",
        "contract_id",
        "contract_sha256",
        "execution",
        "infrastructure_invalid_conditions",
        "judge_stage",
        "outcome_semantics",
        "schema_version",
        "source",
        "starting_policy_stage",
        "target_scope",
    }
    required = allowed - {"contract_sha256"}
    missing = sorted(required - set(raw))
    extra = sorted(set(raw) - allowed)
    if missing:
        raise LabExecutionContractError(f"contract is missing required fields: {missing}")
    if extra:
        raise LabExecutionContractError(f"contract has unsupported fields: {extra}")
    if raw["schema_version"] != SCHEMA_VERSION:
        raise LabExecutionContractError(f"schema_version must be {SCHEMA_VERSION}")
    invalid_conditions = set(
        _string_list(
            raw["infrastructure_invalid_conditions"],
            "infrastructure_invalid_conditions",
            minimum=1,
        )
    )
    missing_conditions = sorted(_REQUIRED_INVALID_CONDITIONS - invalid_conditions)
    if missing_conditions:
        raise LabExecutionContractError(
            "infrastructure_invalid_conditions is missing required conditions: "
            f"{missing_conditions}"
        )
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": _text(raw["contract_id"], "contract_id"),
        "source": _validate_source(raw["source"]),
        "starting_policy_stage": _validate_starting_policy_stage(raw["starting_policy_stage"]),
        "judge_stage": _validate_judge_stage(raw["judge_stage"]),
        "outcome_semantics": _validate_outcome_semantics(raw["outcome_semantics"]),
        "accounting": _validate_accounting(raw["accounting"]),
        "infrastructure_invalid_conditions": sorted(invalid_conditions),
        "target_scope": _validate_target_scope(raw["target_scope"]),
        "execution": _validate_execution(raw["execution"]),
    }
    digest = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    materialized = {**normalized, "contract_sha256": f"sha256:{digest}"}
    recorded = raw.get("contract_sha256")
    if recorded is not None and recorded != materialized["contract_sha256"]:
        raise LabExecutionContractError("contract_sha256 does not match the contract content")
    return materialized


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LabExecutionContractError(
            f"cannot read LAB execution contract {path}: {error}"
        ) from error
    if not isinstance(value, dict):
        raise LabExecutionContractError("LAB execution contract must be a JSON object")
    return validate(value)


def write(contract: dict[str, Any], output: Path, force: bool) -> None:
    if output.exists() and not force:
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
