#!/usr/bin/env python3
"""Benchmark release CLI paths with representative installed adapters."""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "environment-processing" / "probe.json"
ADAPTERS = ("finance", "formal", "legal", "materials", "molecular", "robotics")


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, int((len(ordered) - 1) * fraction + 0.999999))
    return ordered[index]


def invoke(command: list[str], environment: dict[str, str]) -> bytes:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        env=environment,
    ).stdout


def measure(
    command: list[str],
    environment: dict[str, str],
    warmups: int,
    samples: int,
) -> dict[str, Any]:
    for _ in range(warmups):
        invoke(command, environment)

    reference: bytes | None = None
    durations: list[float] = []
    for _ in range(samples):
        started = time.perf_counter_ns()
        output = invoke(command, environment)
        durations.append((time.perf_counter_ns() - started) / 1_000_000)
        if reference is None:
            reference = output
        elif output != reference:
            raise SystemExit(f"benchmark output changed between samples: {' '.join(command)}")

    return {
        "samples": samples,
        "median_ms": round(statistics.median(durations), 3),
        "p95_ms": round(percentile(durations, 0.95), 3),
        "minimum_ms": round(min(durations), 3),
    }


def git_revision() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--warmups", type=int, default=3)
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--max-native-p95-ms", type=float, default=50.0)
    parser.add_argument("--max-adapter-median-ms", type=float, default=200.0)
    parser.add_argument("--max-binary-bytes", type=int, default=2_000_000)
    arguments = parser.parse_args()

    binary = arguments.binary.resolve()
    repository = arguments.repository.resolve()
    if not binary.is_file():
        parser.error(f"binary not found: {binary}")
    if arguments.warmups < 0:
        parser.error("--warmups must not be negative")
    if arguments.samples < 2:
        parser.error("--samples must be at least 2")

    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    scenarios: dict[str, list[str]] = {
        "native.version": [str(binary), "--version"],
        "native.qualify": [str(binary), "qualify", str(FIXTURE), "--json"],
        "adapter.list": [str(binary), "adapter", "list", "--json"],
        "adapter.doctor.materials": [
            str(binary),
            "adapter",
            "doctor",
            "materials",
            "--json",
        ],
    }
    for adapter in ADAPTERS:
        scenarios[f"adapter.status.{adapter}"] = [
            str(binary),
            adapter,
            "status",
            "--repository",
            str(repository),
            "--json",
        ]

    with tempfile.TemporaryDirectory(prefix="anarres-benchmark-") as directory:
        manifest = Path(directory) / "environment.json"
        invoke(
            [str(binary), "measure", str(FIXTURE), "--output", str(manifest)],
            environment,
        )
        scenarios["native.validate"] = [str(binary), "validate", str(manifest), "--json"]
        metrics = {
            name: measure(command, environment, arguments.warmups, arguments.samples)
            for name, command in scenarios.items()
        }

    violations = []
    binary_size = binary.stat().st_size
    if binary_size > arguments.max_binary_bytes:
        violations.append(
            f"binary size: {binary_size} bytes exceeds {arguments.max_binary_bytes} bytes"
        )
    for name, metric in metrics.items():
        if name.startswith("native.") or name.startswith("adapter.list"):
            guard_metric = "p95_ms"
            limit = arguments.max_native_p95_ms
        else:
            guard_metric = "median_ms"
            limit = arguments.max_adapter_median_ms
        metric["guard"] = {"metric": guard_metric, "maximum_ms": limit}
        observed = metric[guard_metric]
        if observed > limit:
            violations.append(f"{name}: {guard_metric} {observed:.2f} ms exceeds {limit:.2f} ms")

    report = {
        "schema_version": "anarres.performance-report.v1",
        "revision": git_revision(),
        "system": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "logical_cpus": os.cpu_count(),
        },
        "binary": {
            "path": str(binary),
            "size_bytes": binary_size,
            "maximum_size_bytes": arguments.max_binary_bytes,
        },
        "parameters": {
            "warmups": arguments.warmups,
            "samples": arguments.samples,
        },
        "metrics": metrics,
        "violations": violations,
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if violations:
        raise SystemExit("; ".join(violations))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
