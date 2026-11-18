#!/usr/bin/env python3
"""Recompute the released Square result from compact evaluation records."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_release_gate(candidate_evaluations: list[Path]) -> None:
    gate = json.loads((ROOT / "RELEASE_GATE.json").read_text(encoding="utf-8"))
    if gate.get("status") != "CANDIDATE_RESULTS_COMPLETE__OUTCOMES_UNOPENED":
        raise ValueError("released candidate panel did not pass the outcome-blind gate")
    if gate.get("candidate_outcomes_opened") is not False:
        raise ValueError("release gate was not sealed before candidate outcomes opened")
    if gate.get("candidate_runs") != 15 or gate.get("evaluation_episodes") != 3840:
        raise ValueError("release gate does not cover the frozen candidate evaluation panel")
    if sha256(ROOT / "EXECUTION_FREEZE.json") != gate.get("execution_freeze_sha256"):
        raise ValueError("execution freeze differs from the released gate")

    released = {path.stem: sha256(path) for path in candidate_evaluations}
    gated = {row["run_id"]: row["evaluation_sha256"] for row in gate.get("records", [])}
    if released != gated:
        raise ValueError("released candidate evaluations differ from the outcome-blind gate")


def command(output: Path) -> list[str]:
    candidates = sorted((ROOT / "evaluations" / "candidates").glob("*.json"))
    probes = sorted((ROOT / "evaluations" / "probes").glob("*.json"))
    if len(candidates) != 15 or len(probes) != 3:
        raise ValueError("released evaluation panel is incomplete")
    validate_release_gate(candidates)
    return [
        sys.executable,
        str(ROOT / "scripts" / "score_candidate_results.py"),
        "--candidate-evaluations",
        *(str(path) for path in candidates),
        "--probe-evaluations",
        *(str(path) for path in probes),
        "--candidates",
        str(ROOT / "CANDIDATES.json"),
        "--protocol",
        str(ROOT / "PROTOCOL.json"),
        "--scoring-contract",
        str(ROOT / "SCORING_CONTRACT.json"),
        "--output",
        str(output),
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    subprocess.run(command(args.output), check=True)


if __name__ == "__main__":
    main()
