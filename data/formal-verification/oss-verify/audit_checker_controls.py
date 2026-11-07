#!/usr/bin/env python3
"""Replay OSS Verify's bounded checker controls in two clean workspaces."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from audit_checker_runtime import expected_image_id

SUMMARY = re.compile(
    r"positive controls passed: (?P<positive>\d+) of (?P<positive_total>\d+); "
    r"negative controls refused as claimed: (?P<negative>\d+) of "
    r"(?P<negative_total>\d+); mutation controls: (?P<mutations>[a-z]+)"
)
MUTATIONS = re.compile(r"mutations caught: (?P<caught>\d+) of (?P<total>\d+) kinds")
CONTROL_PATHS = (
    "dune-project",
    "tests",
    "theories",
    "toolchain/allowed-axioms.txt",
)


class AuditError(ValueError):
    """Raised when the upstream control suite does not meet its contract."""


def run(arguments: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative.startswith("_build/"):
            continue
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def parse_control_output(output: str) -> dict[str, Any]:
    summary = SUMMARY.search(output)
    mutations = MUTATIONS.search(output)
    if not summary or not mutations or "check.sh: all controls behave" not in output:
        raise AuditError("checker controls did not emit a complete passing verdict")
    values: dict[str, Any] = {
        key: int(value) if key != "mutations" else value
        for key, value in summary.groupdict().items()
    }
    values["mutations_caught"] = int(mutations.group("caught"))
    values["mutations_total"] = int(mutations.group("total"))
    if values["positive"] != values["positive_total"]:
        raise AuditError("not every positive checker control passed")
    if values["negative"] != values["negative_total"]:
        raise AuditError("not every negative checker control was refused")
    if values["mutations"] != "caught":
        raise AuditError("statement mutation controls did not pass")
    if values["mutations_caught"] != values["mutations_total"]:
        raise AuditError("not every statement mutation was caught")
    return values


def materialize_view(source: Path, target: Path) -> None:
    for relative in CONTROL_PATHS:
        origin = source / relative
        destination = target / relative
        if not origin.exists():
            raise AuditError(f"missing checker control path: {relative}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if origin.is_dir():
            shutil.copytree(origin, destination)
        else:
            shutil.copy2(origin, destination)


def replay_once(image: str, source: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="anarres-oss-verify-controls-") as directory:
        view = Path(directory)
        materialize_view(source, view)
        source_digest = tree_digest(view)
        started = time.monotonic()
        result = run(
            [
                "docker",
                "run",
                "--rm",
                "--platform",
                "linux/amd64",
                "--network",
                "none",
                "--ulimit",
                "stack=-1:-1",
                "-e",
                "HOME=/tmp",
                "-v",
                f"{view}:/work",
                "-w",
                "/work",
                image,
                "sh",
                "-lc",
                "dune build --root . theories tests && ./tests/check.sh",
            ]
        )
        elapsed = time.monotonic() - started
        output = result.stdout + result.stderr
        return {
            "source_sha256": source_digest,
            "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
            "elapsed_seconds": round(elapsed, 3),
            "verdict": parse_control_output(output),
        }


def audit(source: Path, pin: dict[str, Any], repetitions: int) -> dict[str, Any]:
    if repetitions < 2:
        raise AuditError("clean-reset qualification requires at least two repetitions")
    observed_revision = run(["git", "rev-parse", "HEAD"], cwd=source).stdout.strip()
    if observed_revision != pin["commit"]:
        raise AuditError(f"source revision mismatch: {observed_revision}")

    image = pin["images"]["checker"]
    inspected = json.loads(run(["docker", "image", "inspect", image]).stdout)[0]
    if inspected["Id"] != expected_image_id(image):
        raise AuditError("checker image does not match its pinned digest")

    replays = [replay_once(image, source) for _ in range(repetitions)]
    source_digests = {replay["source_sha256"] for replay in replays}
    verdicts = {json.dumps(replay["verdict"], sort_keys=True) for replay in replays}
    if len(source_digests) != 1 or len(verdicts) != 1:
        raise AuditError("clean checker-control replays disagree")

    return {
        "schema_version": "anarres.formal-verification-control-audit.v1",
        "source_id": pin["source_id"],
        "source_revision": observed_revision,
        "checker_image": image,
        "repetitions": replays,
        "checks": {
            "positive_controls": "pass",
            "negative_controls": "pass",
            "statement_mutations": "pass",
            "clean_reset_agreement": "pass",
        },
        "qualification_state": "checker_controls_qualified_proof_replay_pending",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--pin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=2)
    args = parser.parse_args()
    pin = json.loads(args.pin.read_text(encoding="utf-8"))
    report = audit(args.source.resolve(), pin, args.repetitions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"qualified checker controls across {args.repetitions} clean repetitions")


if __name__ == "__main__":
    main()
