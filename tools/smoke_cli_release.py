#!/usr/bin/env python3
"""Exercise a built Anarres binary as an installed user would."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "environment-processing" / "probe.json"


def run(binary: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(binary), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, int((len(ordered) - 1) * fraction + 0.999999))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--max-startup-ms", type=float, default=50.0)
    parser.add_argument("--samples", type=int, default=40)
    arguments = parser.parse_args()
    binary = arguments.binary.resolve()

    if not binary.is_file():
        parser.error(f"binary not found: {binary}")
    if arguments.samples < 2:
        parser.error("--samples must be at least 2")

    version = run(binary, "--version").stdout.strip()
    run(binary, "--help")
    for shell in ("bash", "zsh", "fish", "powershell"):
        completion = run(binary, "generate-shell-completion", shell).stdout
        if "anarres" not in completion:
            raise SystemExit(f"{shell} completion omitted the command name")

    with tempfile.TemporaryDirectory(prefix="anarres-release-smoke-") as directory:
        manifest = Path(directory) / "environment.json"
        qualification = json.loads(run(binary, "qualify", str(FIXTURE), "--json").stdout)
        if qualification["status_counts"]["admitted"] != 2:
            raise SystemExit("qualification fixture produced an unexpected result")
        run(binary, "measure", str(FIXTURE), "--output", str(manifest))
        validation = json.loads(run(binary, "validate", str(manifest), "--json").stdout)
        if not validation["valid"]:
            raise SystemExit("measured fixture failed validation")

    durations = []
    for _ in range(arguments.samples):
        started = time.perf_counter_ns()
        run(binary, "--version")
        durations.append((time.perf_counter_ns() - started) / 1_000_000)

    median_ms = statistics.median(durations)
    p95_ms = percentile(durations, 0.95)
    print(
        json.dumps(
            {
                "binary": str(binary),
                "version": version,
                "samples": arguments.samples,
                "startup_median_ms": round(median_ms, 3),
                "startup_p95_ms": round(p95_ms, 3),
                "maximum_p95_ms": arguments.max_startup_ms,
            },
            sort_keys=True,
        )
    )
    if p95_ms > arguments.max_startup_ms:
        raise SystemExit(f"startup p95 {p95_ms:.2f} ms exceeds {arguments.max_startup_ms:.2f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
