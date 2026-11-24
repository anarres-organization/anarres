#!/usr/bin/env python3
"""Exercise CLI acceptance cases; optionally run synthetic Docker checks on macOS.

Outputs are local validation evidence, not measurements of scientific utility.
Requires Python 3.11+, a built native CLI, and the installed domain adapters.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import platform
import shutil
import subprocess
import tempfile
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS: list[dict] = []
ENV = os.environ.copy()
ENV.pop("PYTHONPATH", None)


def case(name, arguments, expected=0, check=None, *, env=None, cwd=None, executable=None):
    command = [str(executable or BINARY), *(str(value) for value in arguments)]
    started = time.perf_counter()
    problem = None
    code, stdout, stderr = None, "", ""
    try:
        result = subprocess.run(
            command, cwd=cwd or WORK, env=env or ENV, capture_output=True, text=True, timeout=240
        )
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
        passed = result.returncode == expected
        if check is not None:
            passed = bool(check(result)) and passed
        if "panicked at" in result.stderr or "Traceback (most recent call last)" in result.stderr:
            passed = False
            problem = "Unhandled panic or Python traceback"
    except Exception as error:
        passed = False
        problem = repr(error)
    item = {
        "name": name,
        "command": command,
        "expected_exit": expected,
        "exit_code": code,
        "passed": passed,
        "seconds": round(time.perf_counter() - started, 4),
        "stdout": stdout,
        "stderr": stderr,
        "problem": problem,
    }
    RESULTS.append(item)
    print(f"{'PASS' if passed else 'FAIL'} {name}", flush=True)
    return item


def run(name, command, *, env=None, expected=0, check=None, cwd=None):
    return case(name, command[1:], expected, check, env=env, cwd=cwd, executable=command[0])


def payload(result):
    return json.loads(result.stdout)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    return path


def check_cli():
    case("version", ["--version"], check=lambda r: r.stdout.strip() == VERSION)
    case(
        "top-level-help",
        ["--help"],
        check=lambda r: all(
            text in r.stdout
            for text in (
                "demo",
                "init",
                "inspect",
                "qualify",
                "probe",
                "measure",
                "design",
                "validate",
                "adapter",
            )
        ),
    )
    case("no-command-help", [], 2, lambda r: "Usage:" in r.stderr)
    for command in (
        "demo",
        "init",
        "inspect",
        "qualify",
        "probe",
        "measure",
        "design",
        "validate",
        "adapter",
        "generate-shell-completion",
    ):
        case(f"help-{command}", [command, "--help"], check=lambda r: "Usage:" in r.stdout)

    for shell in ("bash", "zsh", "fish", "powershell", "elvish"):
        result = case(
            f"completion-{shell}",
            ["generate-shell-completion", shell],
            check=lambda r: "anarres" in r.stdout and len(r.stdout) > 100,
        )
        script = WORK / f"completion.{shell}"
        script.write_text(result["stdout"])
        if shell in ("bash", "zsh"):
            case(f"completion-{shell}-syntax", ["-n", script], executable=Path(f"/bin/{shell}"))

    bare = ENV.copy()
    bare["PATH"] = "/usr/bin:/bin"
    case(
        "standalone-with-system-path",
        ["--version"],
        env=bare,
        check=lambda r: r.stdout.strip() == VERSION,
    )
    case(
        "empty-adapter-discovery",
        ["adapter", "list", "--json"],
        env=bare,
        check=lambda r: payload(r)["adapters"] == [],
    )
    case(
        "missing-adapter-doctor",
        ["adapter", "doctor", "missing-test-adapter", "--json"],
        1,
        lambda r: bool(r.stdout or r.stderr),
        env=bare,
    )
    case(
        "missing-external-subcommand",
        ["missing-test-adapter", "status"],
        1,
        lambda r: "adapter" in r.stderr.lower(),
        env=bare,
    )

    demo = WORK / "\u4e2d\u6587 \u7a7a\u683c\u76ee\u5f55"
    a, b = demo / "\u73af\u5883\u7532.json", demo / "\u73af\u5883\u4e59.json"
    case(
        "demo-unicode-and-spaces",
        ["demo", "--output", a, "--comparison-output", b],
        check=lambda r: a.is_file() and b.is_file() and "Compatible" in r.stdout,
    )
    case(
        "demo-records-valid",
        ["validate", a, b, "--json"],
        check=lambda r: payload(r)["valid"] and len(payload(r)["records"]) == 2,
    )
    case(
        "demo-compatible-design-json",
        ["design", a, b, "--json"],
        check=lambda r: payload(r)["compatible"] and payload(r)["candidate_count"] == 2,
    )
    case("demo-design-human-table", ["design", a, b], check=lambda r: "ENVIRONMENT" in r.stdout)

    probe = ROOT / "examples/environment-processing/probe.json"
    raw = ROOT / "examples/environment-processing/probe-run"
    case(
        "qualify-policy-probe-json",
        ["qualify", probe, "--json"],
        check=lambda r: (
            payload(r)["status_counts"]
            == {"admitted": 2, "reserve": 1, "repair": 1, "quarantine": 1}
        ),
    )
    case(
        "qualify-raw-attempt-stream",
        ["qualify", raw, "--json"],
        check=lambda r: (
            payload(r)["attempt_count"] == 20 and payload(r)["status_counts"]["repair"] == 1
        ),
    )
    measured = WORK / "measured.json"
    case(
        "measure-json-correct-coordinates",
        ["measure", probe, "--output", measured, "--json"],
        check=lambda r: (
            math.isclose(payload(r)["coordinates"]["rho_per_million_tokens"], 833.3333333333334)
            and math.isclose(payload(r)["coordinates"]["effective_coverage"], 0.6533333333333333)
            and payload(r)["coordinates"]["generated_action_tokens"] == 4200
        ),
    )
    duplicate = WORK / "measured-again.json"
    case(
        "measurement-byte-determinism",
        ["measure", probe, "--output", duplicate],
        check=lambda r: measured.read_bytes() == duplicate.read_bytes(),
    )
    original = measured.read_bytes()
    case(
        "overwrite-refused-without-force",
        ["measure", probe, "--output", measured],
        1,
        lambda r: "already exists" in r.stderr and measured.read_bytes() == original,
    )
    case(
        "explicit-force-overwrite",
        ["measure", probe, "--output", measured, "--force"],
        check=lambda r: measured.read_bytes() == original,
    )
    raw_record = WORK / "raw.json"
    case(
        "measure-raw-attempt-stream",
        ["measure", raw, "--output", raw_record, "--json"],
        check=lambda r: payload(r)["status_counts"]["admitted"] == 2,
    )
    case(
        "validate-raw-and-normalized-record",
        ["validate", raw, raw_record, "--json"],
        check=lambda r: payload(r)["valid"],
    )
    reordered = WORK / "reordered-probe-run"
    shutil.copytree(raw, reordered)
    rows = (reordered / "attempts.jsonl").read_text().splitlines()
    (reordered / "attempts.jsonl").write_text("\n".join(reversed(rows)) + "\n")
    reordered_record = WORK / "raw-reordered.json"
    case(
        "raw-order-independent-digest",
        ["measure", reordered, "--output", reordered_record],
        check=lambda r: (
            json.loads(raw_record.read_text())["manifest_digest"]
            == json.loads(reordered_record.read_text())["manifest_digest"]
        ),
    )

    primary = WORK / "must-not-be-written.json"
    sentinel = WORK / "sentinel.json"
    sentinel.write_text("existing-test-sentinel")
    case(
        "demo-preflight-is-atomic",
        ["demo", "--output", primary, "--comparison-output", sentinel],
        1,
        lambda r: not primary.exists() and sentinel.read_text() == "existing-test-sentinel",
    )
    case(
        "duplicate-environment-rejected",
        ["design", a, a, "--json"],
        1,
        lambda r: not payload(r)["compatible"] and bool(payload(r)["issues"]),
    )

    tampered = json.loads(measured.read_text())
    tampered["coordinates"]["rho_per_million_tokens"] += 1
    tampered_path = write_json(WORK / "tampered.json", tampered)
    case(
        "tampered-record-rejected",
        ["validate", tampered_path, "--json"],
        1,
        lambda r: not payload(r)["valid"] and bool(payload(r)["records"][0]["error"]),
    )

    for name, value in (
        ("malformed-json", "{broken"),
        ("empty-json", "{}"),
        ("unknown-schema", '{"schema_version":"anarres.unsupported-test.v99"}'),
    ):
        path = WORK / f"{name}.json"
        path.write_text(value)
        case(
            name,
            ["validate", path, "--json"],
            1,
            lambda r: not payload(r)["valid"] and bool(payload(r)["records"][0]["error"]),
        )
    case(
        "missing-input-file",
        ["qualify", WORK / "missing-file.json"],
        1,
        lambda r: "could not read" in r.stderr,
    )
    case("missing-required-argument", ["measure", probe], 2, lambda r: "--output" in r.stderr)
    case("design-requires-two-candidates", ["design", a], 2, lambda r: bool(r.stderr))

    base = json.loads(probe.read_text())
    variants = {}
    variants["duplicate-task-id"] = copy.deepcopy(base)
    variants["duplicate-task-id"]["groups"].append(copy.deepcopy(base["groups"][0]))
    variants["negative-token-cost"] = copy.deepcopy(base)
    variants["negative-token-cost"]["groups"][0]["generated_action_tokens"] = -1
    variants["group-size-mismatch"] = copy.deepcopy(base)
    variants["group-size-mismatch"]["groups"][0]["rewards"].pop()
    for name, value in variants.items():
        path = write_json(WORK / f"{name}.json", value)
        case(name, ["qualify", path, "--json"], 1, lambda r: bool(r.stderr))
    policy_variant = copy.deepcopy(base)
    policy_variant["environment_id"] = "synthetic-other-policy-test"
    policy_variant["policy_id"] = "synthetic-incompatible-policy"
    policy_probe = write_json(WORK / "other-policy.json", policy_variant)
    policy_record = WORK / "other-policy-record.json"
    case("prepare-incompatible-policy-record", ["measure", policy_probe, "--output", policy_record])
    case(
        "different-policy-comparison-rejected",
        ["design", a, policy_record, "--json"],
        1,
        lambda r: (
            not payload(r)["compatible"]
            and any("policy" in issue for issue in payload(r)["issues"])
        ),
    )

    raw_duplicate = WORK / "duplicate-attempt-run"
    shutil.copytree(raw, raw_duplicate)
    with (raw_duplicate / "attempts.jsonl").open("a") as stream:
        stream.write(rows[0] + "\n")
    case(
        "duplicate-raw-attempt-rejected",
        ["qualify", raw_duplicate, "--json"],
        1,
        lambda r: "duplicate" in r.stderr,
    )

    adapters = ("finance", "formal", "legal", "materials", "molecular", "robotics", "vulnerability")
    case(
        "all-seven-adapters-discovered",
        ["adapter", "list", "--json"],
        check=lambda r: tuple(item["name"] for item in payload(r)["adapters"]) == adapters,
    )
    for adapter in adapters:
        case(
            f"adapter-{adapter}-doctor",
            ["adapter", "doctor", adapter, "--json"],
            check=lambda r: (
                payload(r)["valid"] and payload(r)["descriptor"]["protocol_version"] == 2
            ),
        )
        case(
            f"adapter-{adapter}-status",
            [adapter, "status", "--repository", ROOT, "--json"],
            check=lambda r: isinstance(payload(r), dict),
        )
    case(
        "explicit-adapter-run",
        ["adapter", "run", "legal", "status", "--repository", ROOT, "--json"],
        check=lambda r: isinstance(payload(r), dict),
    )

    legal = WORK / "\u539f\u59cb \u6cd5\u5f8b\u6765\u6e90"
    shutil.copytree(ROOT / "examples/environment-source/native-environment", legal)
    case(
        "init-native-legal-source",
        [
            "init",
            legal,
            "--adapter",
            "legal",
            "--revision",
            "synthetic-local-fixture-v1",
            "--license",
            "MIT",
            "--json",
        ],
        check=lambda r: (legal / "anarres.toml").is_file(),
    )
    case(
        "inspect-native-legal-source",
        ["inspect", legal, "--json"],
        check=lambda r: payload(r)["qualification_ready"] and not payload(r)["probe_ready"],
    )
    case(
        "qualify-native-legal-source",
        ["qualify", legal, "--json"],
        check=lambda r: (
            payload(r)["status"] == "qualified"
            and not payload(r)["model_responses_read"]
            and not payload(r)["outcomes_read"]
        ),
    )
    case(
        "source-init-overwrite-protection",
        [
            "init",
            legal,
            "--adapter",
            "legal",
            "--revision",
            "synthetic-local-fixture-v1",
            "--license",
            "MIT",
        ],
        1,
        lambda r: "already exists" in r.stderr,
    )
    case(
        "unsupported-policy-probe-clear-error",
        [
            "probe",
            legal,
            "--policy",
            "synthetic-test-policy",
            "--policy-revision",
            "synthetic-local-fixture-v1",
            "--output",
            WORK / "must-not-probe",
        ],
        1,
        lambda r: "probe" in r.stderr.lower() and not (WORK / "must-not-probe").exists(),
    )
    case(
        "raw-source-cannot-be-measured-as-results",
        ["measure", legal, "--output", WORK / "must-not-measure.json"],
        1,
        lambda r: "probe" in r.stderr.lower() and not (WORK / "must-not-measure.json").exists(),
    )

    for domain in ("robotics", "materials", "legal"):
        paths = []
        for suffix in ("a", "b"):
            fixture = ROOT / f"examples/environment-profiles/{domain}-{suffix}.profile-input.json"
            output = WORK / f"{domain}-{suffix}.profile.json"
            case(
                f"{domain}-{suffix}-profile-measure",
                ["measure", fixture, "--output", output, "--json"],
                check=lambda r: payload(r)["schema_version"] == "anarres.environment-profile.v1",
            )
            case(
                f"{domain}-{suffix}-profile-validate",
                ["validate", output, "--json"],
                check=lambda r: payload(r)["valid"],
            )
            paths.append(output)
        case(
            f"{domain}-compatible-profile-panel",
            ["design", *paths, "--json"],
            check=lambda r: payload(r)["compatible"],
        )
    case(
        "cross-domain-comparison-rejected",
        ["design", WORK / "robotics-a.profile.json", WORK / "materials-a.profile.json", "--json"],
        1,
        lambda r: not payload(r)["compatible"],
    )
    case(
        "mixed-manifest-profile-rejected",
        ["design", measured, WORK / "robotics-a.profile.json"],
        1,
        lambda r: bool(r.stderr),
    )
    case("color-disabled-for-pipe", ["qualify", probe], check=lambda r: "\x1b[" not in r.stdout)
    case(
        "json-remains-clean-with-color-always",
        ["--color", "always", "qualify", probe, "--json"],
        check=lambda r: isinstance(payload(r), dict) and "\x1b[" not in r.stdout,
    )


def check_standalone():
    directory = WORK / "copied-native-binary"
    directory.mkdir()
    binary = directory / "anarres"
    shutil.copy2(BINARY, binary)
    empty_path = directory / "empty-path"
    empty_path.mkdir()
    environment = ENV.copy()
    environment["PATH"] = str(empty_path)
    case(
        "copied-version-empty-path",
        ["--version"],
        env=environment,
        cwd=directory,
        executable=binary,
        check=lambda r: r.stdout.strip() == VERSION,
    )
    case(
        "copied-demo-empty-path",
        ["demo"],
        env=environment,
        cwd=directory,
        executable=binary,
        check=lambda r: (directory / ".anarres/demo/environment.json").is_file(),
    )
    case(
        "copied-validate-empty-path",
        ["validate", ".anarres/demo/environment.json", "--json"],
        env=environment,
        cwd=directory,
        executable=binary,
        check=lambda r: payload(r)["valid"],
    )
    case(
        "copied-design-empty-path",
        [
            "design",
            ".anarres/demo/environment.json",
            ".anarres/demo/environment-alternative.json",
            "--json",
        ],
        env=environment,
        cwd=directory,
        executable=binary,
        check=lambda r: payload(r)["compatible"],
    )


def check_docker():
    run(
        "docker-engine-and-compose",
        ["docker", "version", "--format", "{{json .}}"],
        check=lambda r: json.loads(r.stdout)["Server"]["Os"] == "linux",
    )
    run(
        "official-hello-world-container",
        ["docker", "run", "--rm", "--network", "none", "hello-world"],
        check=lambda r: "Hello from Docker!" in r.stdout,
    )
    run("pull-official-alpine-fixture", ["docker", "pull", "alpine:3.22"])
    image = run(
        "resolve-container-image-digest",
        ["docker", "image", "inspect", "alpine:3.22"],
        check=lambda r: bool(json.loads(r.stdout)[0]["RepoDigests"]),
    )
    if image["passed"]:
        digest = json.loads(image["stdout"])[0]["RepoDigests"][0]
        run(
            "real-read-only-networkless-restricted-container",
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                "64",
                "--memory",
                "128m",
                "--cpus",
                "1",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=16m",
                digest,
                "sh",
                "-ec",
                "test -d /sys/class/net/lo; "
                'test -z "$(ip route show default)"; '
                'test -z "$(ip -o -4 addr show scope global)"; '
                'test -z "$(ip -o -6 addr show scope global)"; '
                "test \"$(awk '/^CapEff:/ {print $2}' /proc/self/status)\" = 0000000000000000; "
                "test \"$(awk '/^NoNewPrivs:/ {print $2}' /proc/self/status)\" = 1; "
                'test "$(cat /sys/fs/cgroup/memory.max)" = 134217728; '
                'test "$(cat /sys/fs/cgroup/pids.max)" = 64; '
                "if touch /must-not-write 2>/tmp/readonly-error; then exit 71; fi; "
                "echo temporary-fixture > /tmp/writable; test -s /tmp/writable; "
                "uname -sm; echo isolation-controls-ok",
            ],
            check=lambda r: "Linux aarch64" in r.stdout and "isolation-controls-ok" in r.stdout,
        )
        shared = WORK / "\u4e2d\u6587 \u5171\u4eab\u76ee\u5f55"
        shared.mkdir()
        (shared / "host.txt").write_text("synthetic-mac-host-fixture\n")
        run(
            "mac-unicode-bind-mount-roundtrip",
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--mount",
                f"type=bind,source={shared},target=/work",
                digest,
                "sh",
                "-ec",
                'cat /work/host.txt; printf "container-roundtrip-ok\\n" > '
                '"/work/\u5bb9\u5668\u8f93\u51fa.txt"',
            ],
            check=lambda r: (
                "synthetic-mac-host-fixture" in r.stdout
                and (shared / "\u5bb9\u5668\u8f93\u51fa.txt").read_text()
                == "container-roundtrip-ok\n"
            ),
        )
        build = WORK / "build-context"
        build.mkdir()
        (build / "fixture.txt").write_text("anarres-local-build-ok\n")
        (build / "Dockerfile").write_text(
            f'FROM {digest}\nCOPY fixture.txt /fixture.txt\nCMD ["cat", "/fixture.txt"]\n'
        )
        tag = f"anarres-mac-validation:{os.getpid()}"
        built = run(
            "local-docker-build", ["docker", "build", "--network", "none", "-t", tag, build]
        )
        if built["passed"]:
            run(
                "run-locally-built-container",
                ["docker", "run", "--rm", "--network", "none", tag],
                check=lambda r: r.stdout.strip() == "anarres-local-build-ok",
            )
            run("cleanup-test-built-image", ["docker", "image", "rm", tag])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "target/release/anarres")
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="new output directory for local records and JSON evidence",
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="pull official test images and exercise a running Docker Desktop",
    )
    args = parser.parse_args()
    if platform.system() != "Darwin":
        parser.error("these acceptance checks target macOS")
    BINARY = args.binary.resolve()
    if not BINARY.is_file():
        parser.error(f"binary not found: {BINARY}; build the release CLI first")
    if args.output_dir.exists():
        parser.error("--output-dir must be new; existing evidence is never overwritten")
    for adapter in (
        "finance",
        "formal",
        "legal",
        "materials",
        "molecular",
        "robotics",
        "vulnerability",
    ):
        if shutil.which(f"anarres-{adapter}") is None:
            parser.error(f"missing adapter anarres-{adapter}; run make setup first")
    if args.docker and shutil.which("docker") is None:
        parser.error("--docker requires Docker Desktop and its CLI")
    version = tomllib.loads((ROOT / "crates/anarres-cli/Cargo.toml").read_text())["package"][
        "version"
    ]
    VERSION = f"anarres {version}"
    REPORT = args.output_dir.resolve()
    REPORT.mkdir(parents=True)
    WORK = Path(tempfile.mkdtemp(prefix="acceptance-", dir=REPORT))
    check_cli()
    check_standalone()
    if args.docker:
        check_docker()
    summary = {
        "binary_version": VERSION,
        "docker_requested": args.docker,
        "case_count": len(RESULTS),
        "passed": sum(item["passed"] for item in RESULTS),
        "failed": sum(not item["passed"] for item in RESULTS),
        "cases": RESULTS,
    }
    write_json(REPORT / "results.json", summary)
    print(json.dumps({key: value for key, value in summary.items() if key != "cases"}))
    raise SystemExit(1 if summary["failed"] else 0)
