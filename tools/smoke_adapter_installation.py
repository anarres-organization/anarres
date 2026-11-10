#!/usr/bin/env python3
"""Build and exercise maintained adapters as isolated installed tools."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = (
    "packages/core",
    "packages/environments",
    "packages/finance",
    "packages/legal",
    "data/formal-verification/vero",
    "experiments/robotics/environment-selection/prospective-cupid-can-v141",
    "experiments/ai-for-science/molecular-design/reaction-environment-selection",
    "experiments/ai-for-science/materials-science/mlip-phonon-environment-selection/adapter",
)
ADAPTERS = ("finance", "formal", "legal", "materials", "molecular", "robotics")


def command(*arguments: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        arguments,
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    arguments = parser.parse_args()
    binary = arguments.binary.resolve()
    if not binary.is_file():
        parser.error(f"binary not found: {binary}")

    with tempfile.TemporaryDirectory(prefix="anarres-adapter-smoke-") as temporary:
        root = Path(temporary)
        wheels = root / "wheels"
        environment = root / "environment"
        wheels.mkdir()

        for package in PACKAGES:
            command(
                "uv",
                "build",
                "--wheel",
                "--out-dir",
                str(wheels),
                str(ROOT / package),
            )

        command("uv", "venv", "--python", "3.11", str(environment))
        scripts = environment / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        command(
            "uv",
            "pip",
            "install",
            "--offline",
            "--python",
            str(python),
            *(str(path) for path in sorted(wheels.glob("*.whl"))),
        )

        installed_environment = os.environ.copy()
        installed_environment.pop("PYTHONPATH", None)
        installed_environment["PATH"] = os.pathsep.join(
            [str(scripts), installed_environment.get("PATH", "")]
        )
        listing = json.loads(
            command(
                str(binary),
                "adapter",
                "list",
                "--json",
                cwd=root,
                env=installed_environment,
            )
        )
        discovered = tuple(adapter["name"] for adapter in listing["adapters"])
        if discovered != ADAPTERS:
            raise SystemExit(f"unexpected adapter set: {discovered!r}")

        contracts: dict[str, list[str]] = {}
        statuses: dict[str, str] = {}
        for adapter in ADAPTERS:
            report = json.loads(
                command(
                    str(binary),
                    "adapter",
                    "doctor",
                    adapter,
                    "--json",
                    cwd=root,
                    env=installed_environment,
                )
            )
            if not report["valid"]:
                raise SystemExit(f"adapter {adapter} failed protocol validation")
            contracts[adapter] = report["descriptor"]["measurement_contracts"]
            executable = scripts / f"anarres-{adapter}{'.exe' if os.name == 'nt' else ''}"
            command(str(executable), "--help", cwd=root, env=installed_environment)
            status = json.loads(
                command(
                    str(binary),
                    adapter,
                    "status",
                    "--repository",
                    str(ROOT),
                    "--json",
                    cwd=root,
                    env=installed_environment,
                )
            )
            statuses[adapter] = status.get("status", "reported")

        for wheel in wheels.glob("*.whl"):
            with zipfile.ZipFile(wheel) as archive:
                unwanted = [
                    name
                    for name in archive.namelist()
                    if "__pycache__" in name or name.endswith((".env", ".DS_Store"))
                ]
            if unwanted:
                raise SystemExit(f"unwanted files in {wheel.name}: {unwanted}")

        print(
            json.dumps(
                {
                    "adapters": list(discovered),
                    "contracts": contracts,
                    "statuses": statuses,
                    "wheels": len(list(wheels.glob("*.whl"))),
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
