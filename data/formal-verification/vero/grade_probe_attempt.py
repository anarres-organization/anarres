#!/usr/bin/env python3
"""Freshly rerender and grade one completed Vero policy-probe attempt."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from materialize_probe_task import selected_repository, tree_digest, verify_source


class GradeError(RuntimeError):
    """Raised when an attempt cannot be graded under the frozen Vero contract."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GradeError(f"expected an object in {path.name}")
    return value


def elapsed_seconds(started: str, ended: str) -> float:
    return (datetime.fromisoformat(ended) - datetime.fromisoformat(started)).total_seconds()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-pin", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--benchmark-id", required=True)
    parser.add_argument("--mode", choices=("proof", "codeproof"), required=True)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--attempt-receipt", type=Path, required=True)
    parser.add_argument("--sandbox-receipt", type=Path, required=True)
    parser.add_argument("--vibe-export", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lake-timeout", type=int, default=600)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.output.exists():
        raise GradeError("--output must not exist")
    if args.lake_timeout <= 0:
        raise GradeError("--lake-timeout must be positive")
    output = args.output.absolute()
    output.mkdir(mode=0o700, parents=True)

    source = args.source.resolve(strict=True)
    task = args.task.resolve(strict=True)
    pin = read_json(args.source_pin)
    panel = read_json(args.panel)
    split = read_json(args.split)
    verify_source(source, pin)
    if panel["source_id"] != pin["source_id"] or split["source_revision"] != pin["commit"]:
        raise GradeError("source, panel, and split identities disagree")
    selected = selected_repository(panel, split, args.benchmark_id)
    benchmark_dir = source / "benchmarks" / selected["directory"]

    attempt = read_json(args.attempt_receipt)
    sandbox = read_json(args.sandbox_receipt)
    exported = read_json(args.vibe_export)
    expected_task_id = f"{args.benchmark_id}:{args.mode}"
    if attempt.get("task_id") != expected_task_id or sandbox.get("task_id") != expected_task_id:
        raise GradeError("attempt identity disagrees with the requested grade")
    if attempt.get("attempt_id") != sandbox.get("attempt_id"):
        raise GradeError("launcher and sandbox receipts disagree on attempt identity")
    if attempt.get("launcher_error") is not None or sandbox.get("infrastructure_errors"):
        raise GradeError("infrastructure-invalid attempt cannot be graded as a scientific outcome")
    if attempt.get("task_post_sha256") != tree_digest(task):
        raise GradeError("task changed after the attempt receipt was written")
    if attempt.get("outcome") != exported.get("outcome"):
        raise GradeError("Vibe outcome disagrees with the launcher receipt")

    lean_version = subprocess.run(
        ["lean", "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if lean_version.returncode != 0 or "Lean (version 4.29.1" not in lean_version.stdout:
        raise GradeError("grading host does not provide the pinned Lean 4.29.1 toolchain")

    try:
        from vero.evaluation.runner import run_evaluation
        from vero.generation.benchmark import Benchmark
        from vero.generation.extractor import extract
    except ImportError as error:
        raise GradeError("pinned Vero package is not available to the grader") from error

    benchmark = Benchmark(benchmark_dir)
    artifact = extract(task, benchmark, mode=args.mode)
    artifact_record = asdict(artifact)
    artifact_record["sandbox_dir"] = "model-visible-task"
    artifact_path = output / "artifact.json"
    artifact_path.write_text(
        json.dumps(artifact_record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    evaluation = run_evaluation(
        benchmark_dir=benchmark_dir,
        artifact=artifact,
        mode=args.mode,
        eval_sandbox_dir=output / "fresh-evaluation-sandbox",
        report_dir=output / "fresh-grade",
        lake_timeout=args.lake_timeout,
    )
    report_path = evaluation.json_path
    report = read_json(report_path)
    report["sandbox_dir"] = "fresh-evaluation-sandbox"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    specs = report["specs"]
    summary = report["summary"]
    forbidden_axiom_statuses = {"uses_sorry", "uses_user_axiom"}
    axiom_checks = report.get("axiom_checks") or []
    approved_axioms = not any(
        record.get("status") in forbidden_axiom_statuses for record in axiom_checks
    )
    per_specification = [
        {
            "module": record["module"],
            "specification": record["spec"],
            "status": record["status"],
            "strict_reward": int(record["status"] == "passed"),
        }
        for record in specs
    ]
    usage = exported.get("usage") or {}
    methods = sandbox.get("methods") or {}
    grade_receipt = {
        "schema_version": "anarres.formal-verification-grade.v1",
        "attempt_id": attempt["attempt_id"],
        "task_id": expected_task_id,
        "source_id": pin["source_id"],
        "benchmark_id": args.benchmark_id,
        "mode": args.mode,
        "infrastructure_valid": True,
        "fresh_grade_build_ok": bool(report["build"]["ok"]),
        "repository_fully_solved": summary["passed_specs"] == summary["total_specs"],
        "specifications_total": summary["total_specs"],
        "specifications_passed": summary["passed_specs"],
        "specifications_unfilled": summary["unfilled_specs"],
        "specifications_failed": summary["failed_specs"],
        "specifications_overfilled": summary["overfilled_specs"],
        "specifications_unpaired_sat": summary["unpaired_sat_specs"],
        "approved_axiom_check": approved_axioms,
        "unexpected_marker_count": len(artifact.extras),
        "artifact_slot_error_count": sum(bool(slot.error) for slot in artifact.slots),
        "artifact_file_error_count": len(artifact.file_errors),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "model_tokens": usage.get("total_tokens"),
        "tool_calls": methods.get("sandbox/execute", 0) + methods.get("sandbox/readFile", 0),
        "wall_seconds": elapsed_seconds(attempt["started_at"], attempt["ended_at"]),
        "peak_memory_bytes": sandbox.get("peak_memory_bytes"),
        "stop_reason": exported.get("stop_reason"),
        "outcome": exported.get("outcome"),
        "per_specification": per_specification,
        "hashes": {
            "task_post_sha256": tree_digest(task),
            "attempt_receipt_sha256": digest(args.attempt_receipt),
            "sandbox_receipt_sha256": digest(args.sandbox_receipt),
            "vibe_export_sha256": digest(args.vibe_export),
            "artifact_sha256": digest(artifact_path),
            "fresh_grade_sha256": digest(report_path),
        },
    }
    (output / "grade-receipt.json").write_text(
        json.dumps(grade_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
