#!/usr/bin/env python3
"""Recompute the released Square result from compact evaluation records."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def command(output: Path) -> list[str]:
    candidates = sorted((ROOT / "evaluations" / "candidates").glob("*.json"))
    probes = sorted((ROOT / "evaluations" / "probes").glob("*.json"))
    if len(candidates) != 15 or len(probes) != 3:
        raise ValueError("released evaluation panel is incomplete")
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
