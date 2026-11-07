#!/usr/bin/env python3
"""Qualify Vero no-op grading and clean resets on the development oracle panel."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

MODES = ("proof", "codeproof")


class AuditError(ValueError):
    """Raised when the model-facing task lifecycle violates its contract."""


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def semantic_result(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "benchmark_id": run["benchmark_id"],
        "mode": run["mode"],
        "artifact_slots": run["artifact_slots"],
        "artifact_extras": run["artifact_extras"],
        "build_ok": run["build_ok"],
        "summary": run["summary"],
        "spec_statuses": run["spec_statuses"],
    }


def validate_noop(run: dict[str, Any], expected_specs: int) -> None:
    summary = run["summary"]
    if run["artifact_extras"] != 0:
        raise AuditError("a pristine sandbox contains marker slots outside its manifest")
    if not run["build_ok"]:
        raise AuditError("an unchanged sandbox was not infrastructure-valid")
    if summary["total_specs"] != expected_specs:
        raise AuditError("the grader reported an unexpected specification count")
    if summary["passed_specs"] != 0 or summary["unfilled_specs"] != expected_specs:
        raise AuditError("an unchanged sandbox did not grade entirely as unfilled")
    if summary["failed_specs"] != 0 or summary["overfilled_specs"] != 0:
        raise AuditError("an unchanged sandbox produced a scientific failure status")
    if set(run["spec_statuses"]) != {"unfilled"}:
        raise AuditError("an unchanged sandbox produced a non-unfilled specification")


def replay_once(benchmark_dir: Path, mode: str, lake_timeout: int) -> dict[str, Any]:
    from vero.evaluation.runner import run_evaluation
    from vero.generation.benchmark import Benchmark
    from vero.generation.extractor import extract
    from vero.generation.sandbox import create_sandbox

    with tempfile.TemporaryDirectory(prefix="anarres-vero-lifecycle-") as directory:
        root = Path(directory)
        agent_sandbox = root / "agent"
        eval_sandbox = root / "eval"
        report_dir = root / "report"
        create_sandbox(benchmark_dir, agent_sandbox, mode=mode)
        artifact = extract(agent_sandbox, Benchmark(benchmark_dir), mode=mode)
        started = time.monotonic()
        result = run_evaluation(
            benchmark_dir=benchmark_dir,
            artifact=artifact,
            mode=mode,
            eval_sandbox_dir=eval_sandbox,
            report_dir=report_dir,
            lake_timeout=lake_timeout,
        )
        elapsed = time.monotonic() - started
        statuses = Counter(spec.status for spec in result.report.specs)
        return {
            "benchmark_id": result.report.benchmark_id,
            "mode": mode,
            "artifact_slots": len(artifact.slots),
            "artifact_extras": len(artifact.extras),
            "build_ok": result.report.build_ok,
            "summary": asdict(result.report.summary),
            "spec_statuses": dict(sorted(statuses.items())),
            "elapsed_seconds": round(elapsed, 3),
            "report_sha256": file_digest(result.json_path),
        }


def run_timeout_control(source: Path) -> dict[str, Any]:
    started = time.monotonic()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/generation/test_base_agent.py::test_base_agent_timeout_fires",
        ],
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
    )
    elapsed = time.monotonic() - started
    output = result.stdout + result.stderr
    if "1 passed" not in output:
        raise AuditError("the model-facing timeout control did not pass")
    return {
        "status": "pass",
        "elapsed_seconds": round(elapsed, 3),
        "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
    }


def verify_panel(
    source: Path,
    pin: dict[str, Any],
    split: dict[str, Any],
    panel: dict[str, Any],
) -> list[dict[str, Any]]:
    revision = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if revision != pin["commit"] or split["source_revision"] != revision:
        raise AuditError("source, pin, and repository split revisions disagree")
    if panel["source_id"] != pin["source_id"]:
        raise AuditError("the lifecycle panel and source pin identify different sources")
    split_by_id = {record["benchmark_id"]: record for record in split["repositories"]}
    records = []
    for selected in panel["repositories"]:
        record = split_by_id.get(selected["benchmark_id"])
        if record is None or record["split"] != "development":
            raise AuditError("the oracle panel contains a non-development repository")
        if record["directory"] != selected["directory"]:
            raise AuditError("the oracle panel directory disagrees with the frozen split")
        if record["source_language"] != selected["source_language"]:
            raise AuditError("the oracle panel language disagrees with the frozen split")
        if record["specifications"] != selected["specifications"]:
            raise AuditError("the oracle panel specification count disagrees with the frozen split")
        benchmark_dir = source / "benchmarks" / record["directory"]
        if not benchmark_dir.is_dir():
            raise AuditError(f"missing benchmark directory: {record['directory']}")
        records.append({**record, "benchmark_dir": benchmark_dir})
    if len({record["source_language"] for record in records}) != len(records):
        raise AuditError("the oracle panel must contain one repository per source language")
    return records


def audit(
    source: Path,
    pin: dict[str, Any],
    split: dict[str, Any],
    panel: dict[str, Any],
    *,
    repetitions: int,
    lake_timeout: int,
) -> dict[str, Any]:
    if repetitions < 2:
        raise AuditError("clean-reset qualification requires at least two repetitions")
    records = verify_panel(source, pin, split, panel)
    results = []
    for record in records:
        for mode in MODES:
            replays = [
                replay_once(record["benchmark_dir"], mode, lake_timeout) for _ in range(repetitions)
            ]
            for replay in replays:
                validate_noop(replay, record["specifications"])
            semantics = {json.dumps(semantic_result(replay), sort_keys=True) for replay in replays}
            if len(semantics) != 1:
                raise AuditError("clean no-op replays disagree")
            results.append(
                {
                    "benchmark_id": record["benchmark_id"],
                    "source_language": record["source_language"],
                    "specifications": record["specifications"],
                    "mode": mode,
                    "repetitions": replays,
                }
            )
    return {
        "schema_version": "anarres.formal-verification-task-lifecycle-audit.v1",
        "source_id": pin["source_id"],
        "panel": panel["selection_rule"],
        "checks": {
            "fresh_sandbox": "pass",
            "manifest_marker_agreement": "pass",
            "unchanged_submission_is_unfilled": "pass",
            "infrastructure_and_scientific_outcomes_separated": "pass",
            "proof_and_codeproof_modes": "pass",
            "clean_reset_agreement": "pass",
            "agent_timeout_control": "pass",
        },
        "agent_timeout_control": run_timeout_control(source),
        "results": results,
        "qualification_state": "noop_and_reset_qualified_policy_probe_pending",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--pin", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--lake-timeout", type=int, default=600)
    args = parser.parse_args()
    report = audit(
        args.source.resolve(),
        json.loads(args.pin.read_text(encoding="utf-8")),
        json.loads(args.split.read_text(encoding="utf-8")),
        json.loads(args.panel.read_text(encoding="utf-8")),
        repetitions=args.repetitions,
        lake_timeout=args.lake_timeout,
    )
    report["split_sha256"] = file_digest(args.split)
    report["panel_sha256"] = file_digest(args.panel)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("qualified Vero no-op grading and clean resets on the development panel")


if __name__ == "__main__":
    main()
