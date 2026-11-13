#!/usr/bin/env python3
"""Reproduce compact released study records without hiding domain boundaries."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class StudyCheck:
    name: str
    cwd: Path
    command: tuple[str, ...]
    extended: bool = False


def python_check(name: str, directory: str, *arguments: str) -> StudyCheck:
    return StudyCheck(name, ROOT / directory, (sys.executable, *arguments))


CHECKS = (
    python_check(
        "mathematics study integrity",
        "experiments/mathematics/environment-utility",
        "scripts/audit_study.py",
    ),
    python_check(
        "mathematics pre-RL measurements",
        "experiments/mathematics/environment-utility",
        "scripts/summarize_prerl.py",
    ),
    python_check(
        "mathematics result tables",
        "experiments/mathematics/environment-utility",
        "scripts/reproduce_tables.py",
    ),
    python_check(
        "formal-verification public evidence",
        "experiments/cyber/formal-verification/public-evidence",
        "test_reproduce.py",
    ),
    python_check(
        "robotics prospective PushT",
        "experiments/robotics/environment-selection/prospective-pusht",
        "test_reproduce.py",
    ),
    python_check(
        "robotics prospective Can",
        "experiments/robotics/environment-selection/prospective-cupid-can-v141",
        "test_released_results.py",
    ),
    python_check(
        "robotics external checks",
        "experiments/robotics/environment-selection/external-checks",
        "test_reproduce.py",
    ),
    python_check(
        "robotics Square prospective contract",
        "experiments/robotics/environment-selection/prospective-square-regression-v1",
        "-m",
        "unittest",
        "discover",
        "-p",
        "test_*.py",
    ),
    python_check(
        "legal prospective SylloGym",
        "experiments/legal/environment-selection",
        "test_reproduce.py",
    ),
    python_check(
        "legal LAB regression report",
        "experiments/legal/lab-learning-dynamics",
        "test_reproduce.py",
    ),
    python_check(
        "materials phonon release",
        "experiments/ai-for-science/materials-science/phonon-environment-selection",
        "-m",
        "unittest",
        "discover",
        "-p",
        "test_*.py",
    ),
    python_check(
        "finance retrospective summary",
        "experiments/finance/retrospective-post-training",
        "test_reproduce.py",
    ),
    python_check(
        "molecular endpoint contract",
        "experiments/ai-for-science/molecular-design/reaction-environment-selection",
        "scripts/verify_qualifying_hit_contract.py",
    ),
    python_check(
        "molecular matched training contract",
        "experiments/ai-for-science/molecular-design/reaction-environment-selection",
        "scripts/verify_matched_training_contract.py",
    ),
    python_check(
        "molecular prospective workflow",
        "experiments/ai-for-science/molecular-design/reaction-environment-selection",
        "-m",
        "unittest",
        "test_gate_endpoint_evaluation.py",
        "test_construct_prospective_banks.py",
        "test_prospective_decision_pipeline.py",
        "test_prospective_release.py",
    ),
    python_check(
        "molecular retrospective bridge",
        "experiments/ai-for-science/molecular-design/retrospective-bridge",
        "test_reproduce.py",
    ),
    python_check(
        "molecular antibody acquisition panel",
        "experiments/ai-for-science/molecular-design/prospective-antibody-acquisition",
        "test_released_results.py",
    ),
    python_check(
        "molecular protein acquisition panel",
        "experiments/ai-for-science/molecular-design/prospective-protein-acquisition",
        "test_released_results.py",
    ),
    StudyCheck(
        "formal-verification adapter",
        ROOT,
        ("anarres-formal", "verify", "--repository", str(ROOT), "--json"),
    ),
    StudyCheck(
        "robotics adapter",
        ROOT,
        ("anarres-robotics", "verify", "--repository", str(ROOT), "--json"),
    ),
    StudyCheck(
        "robotics prospective PushT report",
        ROOT,
        ("anarres-robotics", "results", "--repository", str(ROOT), "--json"),
    ),
    StudyCheck(
        "robotics prospective Can report",
        ROOT,
        ("anarres-robotics", "can-results", "--repository", str(ROOT), "--json"),
    ),
    StudyCheck(
        "legal adapter",
        ROOT,
        ("anarres-legal", "verify", "--repository", str(ROOT), "--json"),
    ),
    StudyCheck(
        "materials adapter",
        ROOT,
        ("anarres-materials", "verify", "--repository", str(ROOT), "--json"),
    ),
    StudyCheck(
        "molecular adapter",
        ROOT,
        ("anarres-molecular", "verify", "--repository", str(ROOT), "--json"),
    ),
    StudyCheck(
        "molecular acquisition reports",
        ROOT,
        (
            "anarres-molecular",
            "acquisition-results",
            "--repository",
            str(ROOT),
            "--json",
        ),
    ),
    StudyCheck(
        "finance compact verification",
        ROOT,
        ("anarres-finance", "verify", "--repository", str(ROOT), "--json"),
    ),
    StudyCheck(
        "finance exhaustive isolated reproduction",
        ROOT,
        (
            "anarres-finance",
            "verify",
            "--exhaustive",
            "--repository",
            str(ROOT),
            "--json",
        ),
        extended=True,
    ),
)


def repository_state() -> str:
    completed = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def require_commands(checks: list[StudyCheck]) -> None:
    missing = sorted(
        {
            check.command[0]
            for check in checks
            if os.sep not in check.command[0] and shutil.which(check.command[0]) is None
        }
    )
    if missing:
        names = ", ".join(missing)
        raise SystemExit(f"missing study-check commands: {names}; run `make setup` first")


def run(check: StudyCheck) -> None:
    started = time.monotonic()
    completed = subprocess.run(
        check.command,
        cwd=check.cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.monotonic() - started
    if completed.returncode != 0:
        print(f"FAIL  {check.name} ({elapsed:.2f}s)", file=sys.stderr)
        if completed.stdout:
            print(completed.stdout.rstrip(), file=sys.stderr)
        if completed.stderr:
            print(completed.stderr.rstrip(), file=sys.stderr)
        raise SystemExit(completed.returncode)
    print(f"PASS  {check.name} ({elapsed:.2f}s)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reproduce compact Anarres study records and maintained adapters."
    )
    parser.add_argument(
        "--extended",
        action="store_true",
        help="also run exhaustive checks that may take several minutes",
    )
    parser.add_argument("--list", action="store_true", help="list checks without running them")
    arguments = parser.parse_args()

    checks = [check for check in CHECKS if arguments.extended or not check.extended]
    if arguments.list:
        for check in checks:
            suffix = " [extended]" if check.extended else ""
            print(f"{check.name}{suffix}")
        return 0

    require_commands(checks)
    before = repository_state()
    started = time.monotonic()
    for check in checks:
        run(check)
    after = repository_state()
    if after != before:
        print("FAIL  study reproduction changed the repository state", file=sys.stderr)
        print(after, file=sys.stderr)
        return 1
    print(f"\nAll {len(checks)} study checks passed in {time.monotonic() - started:.2f}s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
