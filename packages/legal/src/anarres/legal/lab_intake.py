"""Build an outcome-blind workflow inventory from a Harvey LAB checkout."""

from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path
from typing import Any


class LabIntakeError(ValueError):
    """Raised when a LAB checkout cannot support a qualified inventory."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LabIntakeError(f"cannot read LAB task specification {path}: {error}") from error
    if not isinstance(value, dict):
        raise LabIntakeError(f"LAB task specification must be a JSON object: {path}")
    return value


def require_text(value: Any, field: str, task_id: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LabIntakeError(f"{task_id}: {field} must be non-empty text")
    return value.strip()


def require_string_list(value: Any, field: str, task_id: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise LabIntakeError(f"{task_id}: {field} must be a list of strings")
    return value


def task_paths(lab_root: Path) -> list[Path]:
    tasks_root = lab_root / "tasks"
    if not tasks_root.is_dir():
        raise LabIntakeError(f"LAB tasks directory is missing: {tasks_root}")
    paths = sorted(tasks_root.rglob("task.json"))
    if not paths:
        raise LabIntakeError(f"no task.json files found under {tasks_root}")
    return paths


def inspect_task(
    lab_root: Path,
    path: Path,
    source_revision: str,
    document_cache: dict[Path, tuple[int, dict[str, int], str]],
) -> dict[str, Any]:
    task = read_object(path)
    relative = path.relative_to(lab_root / "tasks")
    task_id = relative.parent.as_posix()
    practice_area = relative.parts[0]
    title = require_text(task.get("title"), "title", task_id)
    instructions = require_text(task.get("instructions"), "instructions", task_id)
    raw_work_type = task.get("work_type")
    work_type = (
        raw_work_type.strip()
        if isinstance(raw_work_type, str) and raw_work_type.strip()
        else "unknown"
    )
    tags = require_string_list(task.get("tags"), "tags", task_id)

    deliverables = task.get("deliverables")
    if not isinstance(deliverables, dict) or not deliverables:
        raise LabIntakeError(f"{task_id}: deliverables must be a non-empty object")
    if any(not isinstance(name, str) or not name for name in deliverables):
        raise LabIntakeError(f"{task_id}: every deliverable key must be non-empty text")

    criteria = task.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise LabIntakeError(f"{task_id}: criteria must be a non-empty list")
    criterion_ids: set[str] = set()
    referenced_deliverables: set[str] = set()
    explicit_sources: set[str] = set()
    criteria_with_sources = 0
    for index, criterion in enumerate(criteria):
        if not isinstance(criterion, dict):
            raise LabIntakeError(f"{task_id}: criterion {index} must be an object")
        criterion_id = require_text(criterion.get("id"), f"criteria[{index}].id", task_id)
        if criterion_id in criterion_ids:
            raise LabIntakeError(f"{task_id}: duplicate criterion id {criterion_id}")
        criterion_ids.add(criterion_id)
        require_text(criterion.get("title"), f"criteria[{index}].title", task_id)
        require_text(
            criterion.get("match_criteria"),
            f"criteria[{index}].match_criteria",
            task_id,
        )
        scoped = require_string_list(
            criterion.get("deliverables"),
            f"criteria[{index}].deliverables",
            task_id,
        )
        if not scoped:
            raise LabIntakeError(f"{task_id}: criterion {criterion_id} has no deliverable scope")
        unknown = sorted(set(scoped) - set(deliverables))
        if unknown:
            raise LabIntakeError(
                f"{task_id}: criterion {criterion_id} references unknown deliverables {unknown}"
            )
        referenced_deliverables.update(scoped)
        sources = require_string_list(
            criterion.get("sources"),
            f"criteria[{index}].sources",
            task_id,
        )
        explicit_sources.update(sources)
        criteria_with_sources += int(bool(sources))

    raw_docs_dir = task.get("docs_dir", "documents")
    if not isinstance(raw_docs_dir, str) or not raw_docs_dir.strip():
        raise LabIntakeError(f"{task_id}: docs_dir must be non-empty text when provided")
    document_root = (path.parent / raw_docs_dir).resolve()
    try:
        document_root.relative_to(lab_root.resolve())
    except ValueError as error:
        raise LabIntakeError(f"{task_id}: docs_dir resolves outside the LAB checkout") from error
    if document_root not in document_cache:
        document_files = (
            sorted(item for item in document_root.rglob("*") if item.is_file())
            if document_root.is_dir()
            else []
        )
        extensions = collections.Counter(item.suffix.lower() or "<none>" for item in document_files)
        document_identity = "".join(
            f"{item.relative_to(document_root).as_posix()}\t{sha256(item)}\n"
            for item in document_files
        )
        document_cache[document_root] = (
            len(document_files),
            dict(sorted(extensions.items())),
            hashlib.sha256(document_identity.encode()).hexdigest(),
        )
    document_count, document_extensions, document_set_sha256 = document_cache[document_root]
    unscoped = sorted(set(deliverables) - referenced_deliverables)
    return {
        "schema_version": "anarres.legal-lab-workflow-component.v1",
        "task_id": task_id,
        "practice_area": practice_area,
        "title": title,
        "work_type": work_type,
        "work_type_declared": work_type != "unknown",
        "tags": sorted(set(tags)),
        "instruction_character_count": len(instructions),
        "criterion_count": len(criteria),
        "deliverable_count": len(deliverables),
        "deliverable_extensions": dict(
            sorted(
                collections.Counter(
                    Path(name).suffix.lower() or "<none>" for name in deliverables
                ).items()
            )
        ),
        "criteria_with_explicit_sources": criteria_with_sources,
        "explicit_source_reference_count": len(explicit_sources),
        "document_count": document_count,
        "document_extensions": document_extensions,
        "document_set_sha256": f"sha256:{document_set_sha256}",
        "multi_artifact": len(deliverables) > 1,
        "unscoped_deliverables": unscoped,
        "source_revision": source_revision,
        "task_spec_sha256": f"sha256:{sha256(path)}",
        "outcomes_read": False,
        "model_responses_read": False,
    }


def build(lab_root: Path, source_revision: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not source_revision.strip():
        raise LabIntakeError("source revision must be non-empty")
    document_cache: dict[Path, tuple[int, dict[str, int], str]] = {}
    rows = [
        inspect_task(lab_root, path, source_revision, document_cache)
        for path in task_paths(lab_root)
    ]
    task_ids = [row["task_id"] for row in rows]
    if len(task_ids) != len(set(task_ids)):
        raise LabIntakeError("LAB task identities are not unique")
    areas = collections.Counter(row["practice_area"] for row in rows)
    work_types = collections.Counter(row["work_type"] for row in rows)
    tasks_with_documents = sum(row["document_count"] > 0 for row in rows)
    status = "qualified" if tasks_with_documents == len(rows) else "incomplete_matter_files"
    task_set_digest = hashlib.sha256(
        "".join(
            (f"{row['task_id']}\t{row['task_spec_sha256']}\t{row['document_set_sha256']}\n")
            for row in rows
        ).encode()
    ).hexdigest()
    summary = {
        "schema_version": "anarres.legal-lab-workflow-intake.v1",
        "status": status,
        "source": {
            "project": "Harvey LAB",
            "repository": "https://github.com/harveyai/harvey-labs",
            "revision": source_revision,
            "license": "MIT",
            "task_set_sha256": f"sha256:{task_set_digest}",
            "identity_includes_matter_documents": True,
        },
        "support": {
            "tasks": len(rows),
            "practice_areas": len(areas),
            "practice_area_counts": dict(sorted(areas.items())),
            "work_type_counts": dict(sorted(work_types.items())),
            "tasks_with_declared_work_type": sum(row["work_type_declared"] for row in rows),
            "rubric_criteria": sum(row["criterion_count"] for row in rows),
            "tasks_with_multiple_deliverables": sum(row["multi_artifact"] for row in rows),
            "tasks_with_explicit_source_scoping": sum(
                row["criteria_with_explicit_sources"] > 0 for row in rows
            ),
            "tasks_with_documents": tasks_with_documents,
        },
        "qualification": {
            "task_identity": "pass",
            "instructions": "pass",
            "rubric_contract": "pass",
            "deliverable_scoping": "pass",
            "matter_documents": "pass" if tasks_with_documents == len(rows) else "incomplete",
        },
        "frontier_workflow_fields": {
            "native": [
                "practice_area",
                "work_type",
                "matter_documents",
                "instructions",
                "deliverables",
                "criterion_level_review_contract",
            ],
            "requires_run_artifacts": [
                "model_and_checkpoint_identity",
                "harness_and_tool_contract",
                "compaction_and_context_contract",
                "judge_identity_and_grader_profile",
                "criterion_verdicts",
                "all_pass",
                "document_coverage",
                "tool_use",
                "artifact_completion",
                "latency_and_token_cost",
                "infrastructure_failures",
            ],
            "requires_supplemental_metadata_when_relevant": [
                "jurisdiction",
                "effective_date_cutoff",
                "authority_hierarchy",
                "workflow_stage",
                "risk_or_guardrail_class",
            ],
        },
        "evaluation_contract": {
            "headline": "task_all_pass",
            "diagnostics": [
                "criterion_pass_rate_macro",
                "criterion_pass_rate_pooled",
                "practice_area_performance",
                "workflow_performance",
                "regression_from_starting_policy",
                "reliability_and_cost",
            ],
            "independent_unit": "training_intervention",
            "nested_units": ["checkpoint", "task", "rubric_criterion", "judge"],
        },
        "profile_input": False,
        "outcomes_read": False,
        "model_responses_read": False,
        "claim_boundary": (
            "This intake qualifies the target workflow and evaluation structure. "
            "It does not measure a starting policy or predict downstream training utility."
        ),
    }
    return summary, rows


def write(
    summary: dict[str, Any], rows: list[dict[str, Any]], output_dir: Path, force: bool
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = [output_dir / "lab-workflow-summary.json", output_dir / "lab-workflow-components.jsonl"]
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
