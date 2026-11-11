#!/usr/bin/env python3
"""Build and exercise maintained adapters as isolated installed tools."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
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
ADAPTER_PACKAGES = {
    "finance": "packages/finance",
    "formal": "data/formal-verification/vero",
    "legal": "packages/legal",
    "materials": (
        "experiments/ai-for-science/materials-science/mlip-phonon-environment-selection/adapter"
    ),
    "molecular": "experiments/ai-for-science/molecular-design/reaction-environment-selection",
    "robotics": "experiments/robotics/environment-selection/prospective-cupid-can-v141",
}


def command(*arguments: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    try:
        result = subprocess.run(
            arguments,
            cwd=cwd,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        if error.stdout:
            print(error.stdout, end="")
        if error.stderr:
            print(error.stderr, end="", file=sys.stderr)
        raise
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
        source_formats: dict[str, list[str]] = {}
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
            source_formats[adapter] = report["descriptor"].get("source_formats", [])
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

        native_source = root / "native-source" / "robotics-can"
        native_source.mkdir(parents=True)
        native_dataset = native_source / "can.hdf5"
        command(
            str(python),
            "-c",
            (
                "import h5py,sys; "
                "h=h5py.File(sys.argv[1],'w'); "
                "h.create_group('data').create_group('demo_0'); h.close()"
            ),
            str(native_dataset),
            cwd=root,
            env=installed_environment,
        )
        native_digest = hashlib.sha256(native_dataset.read_bytes()).hexdigest()
        command(
            str(binary),
            "init",
            str(native_source),
            "--adapter",
            "robotics",
            "--revision",
            f"sha256:{native_digest}",
            "--license",
            "test-fixture",
            cwd=root,
            env=installed_environment,
        )
        native_inspection = json.loads(
            command(
                str(binary),
                "inspect",
                str(native_source),
                "--json",
                cwd=root,
                env=installed_environment,
            )
        )
        if not native_inspection["qualification_ready"]:
            raise SystemExit(f"robotics source was not routed: {native_inspection!r}")
        if native_inspection["probe_ready"]:
            raise SystemExit("robotics source unexpectedly claims a policy probe runtime")
        rejected_source = subprocess.run(
            [str(binary), "qualify", str(native_source), "--json"],
            cwd=root,
            env=installed_environment,
            check=False,
            capture_output=True,
            text=True,
        )
        if rejected_source.returncode != 1 or "pinned Can v1.4.1" not in rejected_source.stderr:
            raise SystemExit(
                "robotics source identity mismatch was not rejected precisely: "
                f"{rejected_source.stderr!r}"
            )

        molecular_source = root / "native-source" / "molecular-q07820"
        shutil.copytree(
            ROOT / "tests/fixtures/molecular-source-v1",
            molecular_source,
        )
        molecular_digest = json.loads(
            command(
                str(binary),
                "molecular",
                "source-digest",
                "--source",
                str(molecular_source),
                "--json",
                cwd=root,
                env=installed_environment,
            )
        )["revision"]
        command(
            str(binary),
            "init",
            str(molecular_source),
            "--adapter",
            "molecular",
            "--revision",
            molecular_digest,
            "--license",
            "mixed-public-sources",
            cwd=root,
            env=installed_environment,
        )
        molecular_inspection = json.loads(
            command(
                str(binary),
                "inspect",
                str(molecular_source),
                "--json",
                cwd=root,
                env=installed_environment,
            )
        )
        if not molecular_inspection["qualification_ready"]:
            raise SystemExit(f"molecular source was not routed: {molecular_inspection!r}")
        if not molecular_inspection["probe_ready"]:
            raise SystemExit("molecular source did not expose its policy probe path")
        molecular_qualification = json.loads(
            command(
                str(binary),
                "qualify",
                str(molecular_source),
                "--json",
                cwd=root,
                env=installed_environment,
            )
        )
        if molecular_qualification["candidate_replay_items"] != 2:
            raise SystemExit(
                f"molecular native source did not qualify: {molecular_qualification!r}"
            )
        if molecular_qualification.get("target_id") != "Q07820":
            raise SystemExit(
                f"molecular source qualified the wrong target: {molecular_qualification!r}"
            )

        profile_root = root / "profiles"
        record_root = root / "records"
        profile_count = 0
        record_count = 0
        records_by_adapter: dict[str, list[Path]] = {}
        for adapter in ADAPTERS:
            output_directory = profile_root / adapter
            command(
                str(binary),
                adapter,
                "profile",
                "--repository",
                str(ROOT),
                "--output-dir",
                str(output_directory),
                "--json",
                cwd=root,
                env=installed_environment,
            )
            profiles = sorted(output_directory.glob("*.profile-input.json"))
            if not profiles:
                raise SystemExit(f"adapter {adapter} exported no profile inputs")
            records_by_adapter[adapter] = []
            for profile in profiles:
                profile_count += 1
                command(
                    str(binary),
                    "qualify",
                    str(profile),
                    "--json",
                    cwd=root,
                    env=installed_environment,
                )
                record = (
                    record_root
                    / adapter
                    / profile.name.replace(".profile-input.json", ".profile.json")
                )
                record.parent.mkdir(parents=True, exist_ok=True)
                command(
                    str(binary),
                    "measure",
                    str(profile),
                    "--output",
                    str(record),
                    "--json",
                    cwd=root,
                    env=installed_environment,
                )
                command(
                    str(binary),
                    "validate",
                    str(profile),
                    str(record),
                    "--json",
                    cwd=root,
                    env=installed_environment,
                )
                records_by_adapter[adapter].append(record)
                record_count += 1

        compatible_panels = []
        for adapter in ("legal", "materials", "molecular", "robotics"):
            records = records_by_adapter[adapter]
            if len(records) < 2:
                raise SystemExit(f"adapter {adapter} did not export a candidate panel")
            command(
                str(binary),
                "design",
                str(records[0]),
                str(records[1]),
                "--json",
                cwd=root,
                env=installed_environment,
            )
            compatible_panels.append(adapter)

        formal_records = records_by_adapter["formal"]
        formal_design = subprocess.run(
            [
                str(binary),
                "design",
                str(formal_records[0]),
                str(formal_records[1]),
                "--json",
            ],
            cwd=root,
            env=installed_environment,
            check=False,
            capture_output=True,
            text=True,
        )
        if formal_design.returncode != 1:
            raise SystemExit(
                "formal profiles with distinct contracts were not rejected as incompatible"
            )

        for wheel in wheels.glob("*.whl"):
            with zipfile.ZipFile(wheel) as archive:
                unwanted = [
                    name
                    for name in archive.namelist()
                    if "__pycache__" in name or name.endswith((".env", ".DS_Store"))
                ]
            if unwanted:
                raise SystemExit(f"unwanted files in {wheel.name}: {unwanted}")

        tool_root = root / "source-tools"
        tool_bin = tool_root / "bin"
        source_environment = os.environ.copy()
        source_environment.pop("PYTHONPATH", None)
        source_environment["UV_CACHE_DIR"] = str(tool_root / "cache")
        source_environment["UV_TOOL_DIR"] = str(tool_root / "tools")
        source_environment["UV_TOOL_BIN_DIR"] = str(tool_bin)
        source_environment["PATH"] = os.pathsep.join(
            [str(tool_bin), source_environment.get("PATH", "")]
        )
        for adapter, package in ADAPTER_PACKAGES.items():
            command(
                "uv",
                "tool",
                "install",
                str(ROOT / package),
                cwd=ROOT,
                env=source_environment,
            )
            executable = tool_bin / f"anarres-{adapter}{'.exe' if os.name == 'nt' else ''}"
            descriptor = json.loads(
                command(
                    str(executable),
                    "--anarres-adapter-descriptor",
                    cwd=root,
                    env=source_environment,
                )
            )
            if descriptor["name"] != adapter:
                raise SystemExit(f"source-installed adapter mismatch: {descriptor!r}")

        source_listing = json.loads(
            command(
                str(binary),
                "adapter",
                "list",
                "--json",
                cwd=root,
                env=source_environment,
            )
        )
        source_adapters = tuple(adapter["name"] for adapter in source_listing["adapters"])
        if source_adapters != ADAPTERS:
            raise SystemExit(f"unexpected source-installed adapter set: {source_adapters!r}")

        print(
            json.dumps(
                {
                    "adapters": list(discovered),
                    "contracts": contracts,
                    "source_formats": source_formats,
                    "source_installed_adapters": list(source_adapters),
                    "statuses": statuses,
                    "user_flow": {
                        "compatible_panels": compatible_panels,
                        "formal_incompatibility_rejected": True,
                        "profile_inputs": profile_count,
                        "records": record_count,
                        "molecular_native_source_qualified": True,
                        "robotics_native_source_routed": True,
                        "robotics_unpinned_source_rejected": True,
                    },
                    "wheels": len(list(wheels.glob("*.whl"))),
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
