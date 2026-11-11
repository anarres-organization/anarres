#!/usr/bin/env python3
"""Audit native Harvey LAB run artifacts without assuming a model provider."""

from __future__ import annotations

import collections
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any


class LabRunAuditError(ValueError):
    """Raised when LAB run artifacts violate the audit contract."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LabRunAuditError(f"cannot read LAB run artifact {path}: {error}") from error
    if not isinstance(value, dict):
        raise LabRunAuditError(f"LAB run artifact must be a JSON object: {path}")
    return value


def optional_manifest(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    value = read_object(path)
    runs = value.get("runs")
    if not isinstance(runs, list):
        raise LabRunAuditError("run manifest must contain a runs list")
    result: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(runs):
        if not isinstance(row, dict):
            raise LabRunAuditError(f"run manifest row {index} must be an object")
        run_id = row.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise LabRunAuditError(f"run manifest row {index} has no run_id")
        if run_id in result:
            raise LabRunAuditError(f"duplicate run manifest identity: {run_id}")
        result[run_id] = row
    return result


def dual_score(scores: dict[str, Any]) -> dict[str, Any]:
    judges = scores.get("judges")
    if (
        not isinstance(judges, list)
        or len(judges) != 2
        or any(not isinstance(judge, str) or not judge.strip() for judge in judges)
        or len(set(judges)) != 2
    ):
        raise LabRunAuditError("scores_dual.json must identify two distinct judges")
    criterion_pass = scores.get("dual_criterion_pass")
    all_pass_score = scores.get("dual_all_pass_rate")
    if not isinstance(criterion_pass, (int, float)) or not 0 <= criterion_pass <= 1:
        raise LabRunAuditError("scores_dual.json has invalid dual_criterion_pass")
    if not isinstance(all_pass_score, (int, float)) or not 0 <= all_pass_score <= 1:
        raise LabRunAuditError("scores_dual.json has invalid dual_all_pass_rate")
    strict_all_pass = scores.get("all_pass")
    if not isinstance(strict_all_pass, bool):
        raise LabRunAuditError("scores_dual.json has invalid all_pass")
    return {
        "judge_profile": scores.get("judge_profile", "unlabeled-dual"),
        "judges": judges,
        "criterion_pass_rate": float(criterion_pass),
        "all_pass_score": float(all_pass_score),
        "strict_all_pass": strict_all_pass,
    }


def single_score(scores: dict[str, Any]) -> dict[str, Any]:
    passed = scores.get("n_passed")
    total = scores.get("n_criteria")
    if not isinstance(passed, int) or not isinstance(total, int) or total <= 0:
        raise LabRunAuditError("scores.json has invalid criterion counts")
    if not 0 <= passed <= total:
        raise LabRunAuditError("scores.json has inconsistent criterion counts")
    judge = scores.get("judge_model")
    if not isinstance(judge, str) or not judge.strip():
        raise LabRunAuditError("scores.json has no judge identity")
    return {
        "judge_profile": "single-judge",
        "judges": [judge],
        "criterion_pass_rate": passed / total,
        "all_pass_score": float(passed == total),
        "strict_all_pass": passed == total,
    }


def inspect_run(
    results_root: Path,
    config_path: Path,
    manifest: dict[str, dict[str, Any]],
    execution_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_dir = config_path.parent
    config = read_object(config_path)
    run_id = config.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        run_id = run_dir.relative_to(results_root).as_posix()
    task = config.get("task")
    model = config.get("model")
    if not isinstance(task, str) or not task:
        raise LabRunAuditError(f"{run_id}: config has no task identity")
    if not isinstance(model, str) or not model:
        raise LabRunAuditError(f"{run_id}: config has no model identity")

    metrics_path = run_dir / "metrics.json"
    dual_path = run_dir / "scores_dual.json"
    single_path = run_dir / "scores.json"
    invalid_reasons: list[str] = []
    metrics: dict[str, Any] = {}
    score: dict[str, Any] | None = None
    if not metrics_path.is_file():
        invalid_reasons.append("missing_metrics")
    else:
        try:
            metrics = read_object(metrics_path)
        except LabRunAuditError:
            invalid_reasons.append("invalid_metrics")
        else:
            if metrics.get("finished_cleanly") is not True:
                invalid_reasons.append("run_not_finished_cleanly")
    score_path: Path | None = None
    if dual_path.is_file():
        score_path = dual_path
        try:
            score = dual_score(read_object(dual_path))
        except LabRunAuditError:
            invalid_reasons.append("invalid_judge_score")
    elif single_path.is_file():
        score_path = single_path
        try:
            score = single_score(read_object(single_path))
        except LabRunAuditError:
            invalid_reasons.append("invalid_judge_score")
    else:
        invalid_reasons.append("missing_judge_score")

    manifest_row = manifest.get(run_id, {})
    if execution_contract is not None:
        expected_stage = execution_contract["starting_policy_stage"]
        expected_policy = expected_stage["policy"]
        expected_config = {
            "model": expected_policy["model_id"],
            "max_turns": expected_stage["max_turns"],
            "temperature": expected_stage["temperature"],
            "shell_timeout": expected_stage["shell_timeout_seconds"],
            "reasoning_effort": expected_stage["reasoning_effort"],
            "skills": [skill["id"] for skill in expected_stage["skills"]],
            "sandbox_image": expected_stage["sandbox_image"],
            "enable_finish": expected_stage["finish_tool_enabled"],
        }
        if any(config.get(key) != expected for key, expected in expected_config.items()):
            invalid_reasons.append("execution_contract_mismatch")
        compaction = config.get("compaction")
        actual_strategy = "none" if compaction is None else compaction.get("strategy")
        if actual_strategy != expected_stage["compaction"]["strategy"]:
            invalid_reasons.append("compaction_contract_mismatch")
        required_identity = {
            "contract_id": execution_contract["contract_id"],
            "model_revision": expected_policy["model_revision"],
            "checkpoint_id": expected_policy["checkpoint_id"],
            "checkpoint_revision": expected_policy["checkpoint_revision"],
        }
        if any(manifest_row.get(key) != expected for key, expected in required_identity.items()):
            invalid_reasons.append("runtime_identity_mismatch")
        if score is not None:
            expected_judges = [
                judge["model_id"] for judge in execution_contract["judge_stage"]["judges"]
            ]
            if (
                score["judges"] != expected_judges
                or score["judge_profile"] != execution_contract["judge_stage"]["judge_profile"]
            ):
                invalid_reasons.append("judge_contract_mismatch")

    invalid_reasons = sorted(set(invalid_reasons))
    valid = not invalid_reasons
    practice_area = task.split("/", 1)[0]
    total_documents = metrics.get("total_documents")
    documents_read = metrics.get("documents_read")
    document_coverage = None
    if isinstance(total_documents, int) and total_documents > 0 and isinstance(documents_read, int):
        document_coverage = documents_read / total_documents
    return {
        "schema_version": "anarres.legal-lab-run-audit-row.v1",
        "run_id": run_id,
        "task_id": task,
        "practice_area": practice_area,
        "model_id": model,
        "policy_id": manifest_row.get("policy_id", model),
        "intervention_id": manifest_row.get("intervention_id"),
        "checkpoint": manifest_row.get("checkpoint"),
        "seed": manifest_row.get("seed"),
        "role": manifest_row.get("role", "unspecified"),
        "execution_contract_sha256": (
            execution_contract["contract_sha256"] if execution_contract is not None else None
        ),
        "contract": {
            "reasoning_effort": config.get("reasoning_effort"),
            "temperature": config.get("temperature"),
            "max_turns": config.get("max_turns"),
            "sandbox_image": config.get("sandbox_image"),
            "skills": config.get("skills"),
            "finish_tool_enabled": config.get("enable_finish"),
            "config_sha256": f"sha256:{sha256(config_path)}",
        },
        "valid_scored_run": valid,
        "infrastructure_invalid_reasons": invalid_reasons,
        "finish_reason": metrics.get("finish_reason"),
        "criterion_pass_rate": score["criterion_pass_rate"] if valid and score else None,
        "all_pass_score": score["all_pass_score"] if valid and score else None,
        "strict_all_pass": score["strict_all_pass"] if valid and score else None,
        "judge_profile": score["judge_profile"] if valid and score else None,
        "judges": score["judges"] if valid and score else None,
        "document_coverage": document_coverage if valid else None,
        "documents_read": documents_read if valid else None,
        "total_documents": total_documents if valid else None,
        "turn_count": metrics.get("turn_count") if valid else None,
        "tool_metrics": (
            {
                key: metrics.get(key)
                for key in (
                    "bash_commands",
                    "files_written",
                    "files_edited",
                    "glob_searches",
                    "grep_searches",
                    "finish_called",
                )
            }
            if valid
            else None
        ),
        "input_tokens": metrics.get("input_tokens") if valid else None,
        "output_tokens": metrics.get("output_tokens") if valid else None,
        "wall_clock_seconds": metrics.get("wall_clock_seconds") if valid else None,
        "artifacts": {
            "metrics": f"sha256:{sha256(metrics_path)}" if metrics_path.is_file() else None,
            "scores": f"sha256:{sha256(score_path)}" if score_path else None,
        },
    }


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def build(
    results_root: Path,
    run_manifest: Path | None = None,
    execution_contract: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not results_root.is_dir():
        raise LabRunAuditError(f"LAB results directory is missing: {results_root}")
    manifest = optional_manifest(run_manifest)
    config_paths = sorted(results_root.rglob("config.json"))
    if not config_paths:
        raise LabRunAuditError(f"no LAB config.json files found under {results_root}")
    rows = [inspect_run(results_root, path, manifest, execution_contract) for path in config_paths]
    run_ids = [row["run_id"] for row in rows]
    if len(run_ids) != len(set(run_ids)):
        raise LabRunAuditError("LAB run identities are not unique")
    unknown_manifest = sorted(set(manifest) - set(run_ids))
    if unknown_manifest:
        raise LabRunAuditError(f"run manifest references missing runs: {unknown_manifest}")

    valid = [row for row in rows if row["valid_scored_run"]]
    invalid = [row for row in rows if not row["valid_scored_run"]]
    by_policy: dict[str, dict[str, Any]] = {}
    for policy_id, policy_rows_iterator in itertools.groupby(
        sorted(valid, key=lambda row: row["policy_id"]), key=lambda row: row["policy_id"]
    ):
        policy_rows = list(policy_rows_iterator)
        by_policy[policy_id] = {
            "valid_runs": len(policy_rows),
            "criterion_pass_rate_macro": mean(
                [float(row["criterion_pass_rate"]) for row in policy_rows]
            ),
            "all_pass_rate": mean([float(row["all_pass_score"]) for row in policy_rows]),
            "strict_all_pass_rate": mean([float(row["strict_all_pass"]) for row in policy_rows]),
            "mean_document_coverage": mean(
                [
                    float(row["document_coverage"])
                    for row in policy_rows
                    if row["document_coverage"] is not None
                ]
            ),
            "practice_areas": len({row["practice_area"] for row in policy_rows}),
        }
    summary = {
        "schema_version": "anarres.legal-lab-run-audit.v1",
        "status": "complete" if not invalid else "complete_with_invalid_runs",
        "support": {
            "discovered_runs": len(rows),
            "valid_scored_runs": len(valid),
            "infrastructure_invalid_runs": len(invalid),
            "tasks": len({row["task_id"] for row in rows}),
            "practice_areas": len({row["practice_area"] for row in rows}),
            "policies": len({row["policy_id"] for row in rows}),
        },
        "invalid_reason_counts": dict(
            sorted(
                collections.Counter(
                    reason for row in invalid for reason in row["infrastructure_invalid_reasons"]
                ).items()
            )
        ),
        "policy_summaries": by_policy,
        "outcome_contract": {
            "headline": "all_pass_rate",
            "diagnostics": [
                "criterion_pass_rate_macro",
                "strict_all_pass_rate",
                "document_coverage",
                "tool_use",
                "latency_and_token_cost",
            ],
            "regression_reference": "starting_policy_with_same_task_and_evaluation_contract",
        },
        "profile_input": False,
        "execution_contract": (
            {
                "contract_id": execution_contract["contract_id"],
                "contract_sha256": execution_contract["contract_sha256"],
            }
            if execution_contract is not None
            else None
        ),
        "claim_boundary": (
            "This audit summarizes native LAB runs and preserves invalid executions. "
            "Training effects require matched starting-policy and intervention records."
        ),
    }
    return summary, rows


def write(
    summary: dict[str, Any], rows: list[dict[str, Any]], output_dir: Path, force: bool
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = [output_dir / "lab-run-audit-summary.json", output_dir / "lab-run-audit-rows.jsonl"]
    if not force:
        existing = [path for path in paths if path.exists()]
        if existing:
            raise FileExistsError(existing[0])
    paths[0].write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths[1].write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return paths
