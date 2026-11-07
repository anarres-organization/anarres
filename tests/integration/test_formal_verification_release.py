from __future__ import annotations

import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "data" / "formal-verification" / "oss-verify"


def load_module(name: str, source: Path):
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {source}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(source.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(source.parent))
    return module


AUDIT = load_module("oss_verify_audit_release", ADAPTER / "audit_release.py")
PANEL = load_module("oss_verify_build_panel", ADAPTER / "build_development_panel.py")
RUNTIME = load_module("oss_verify_runtime_audit", ADAPTER / "audit_checker_runtime.py")
CONTROLS = load_module("oss_verify_control_audit", ADAPTER / "audit_checker_controls.py")


def write_fixture(root: Path) -> dict:
    files = {
        "release.yaml": """schema: oss-fuzz-theorems/release/1
release: 2099.1.0
date: '2099-01-02'
semantics:
  commit: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
rocq:
  version: 9.2.0
images:
  checker: checker@sha256:abc
  runner: runner@sha256:def
""",
        "index/projects.tsv": "project\nlib-a\n",
        "index/harnesses.tsv": "project\tharness\nlib-a\tharness-a\nlib-a\tharness-b\n",
        "index/binaries.tsv": (
            "project\tharness\tbuild\tstatus\tbytes\tsha256\n"
            f"lib-a\tharness-a\tplain\tpublished\t4\t{'1' * 64}\n"
            f"lib-a\tharness-b\tplain\tpublished\t5\t{'2' * 64}\n"
        ),
        "index/statements.tsv": (
            "id\tkind\tstatus\trevision\tfingerprint\tproof\n"
            f"lib-a/harness-a/plain_halts\thalts\tproved\t1\t{'3' * 64}\tproof-a\n"
            f"lib-a/harness-a/asan_agrees\tagreement\topen\t1\t{'4' * 64}\t-\n"
            f"lib-a/harness-b/plain_halts\thalts\tproved\t1\t{'5' * 64}\tproof-b\n"
            f"lib-a/harness-b/asan_agrees\tagreement\topen\t1\t{'6' * 64}\t-\n"
        ),
        "index/proofs.tsv": (
            "library\tentry_point\tstatement\tkind\tproof\tstatement_file\n"
            "lib-a\tharness-a\tplain_halts\thalts\tproof-a\tstatement-a\n"
            "lib-a\tharness-b\tplain_halts\thalts\tproof-b\tstatement-b\n"
        ),
        "toolchain/allowed-axioms.txt": "Classical_Prop.classic\n",
        "toolchain/checker.Dockerfile": "FROM scratch\n",
    }
    artifacts = []
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        artifacts.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "media_type": "text/plain",
                "uri": f"https://example.test/release/{relative}",
                "license": "MIT",
                "producing_run_or_upstream_release": "fixture-v1",
            }
        )
    return {
        "schema_version": "anarres.formal-verification-source-pin.v1",
        "source_id": "fixture@v1",
        "release": "2099.1.0",
        "release_date": "2099-01-02",
        "rocq": {"version": "9.2.0"},
        "semantics": {"commit": "a" * 40},
        "images": {"checker": "checker@sha256:abc", "runner": "runner@sha256:def"},
        "artifacts": artifacts,
        "expected_counts": {
            "projects": 1,
            "entry_points": 2,
            "binaries": 2,
            "statements": 4,
            "proofs": 2,
            "proved_entry_points": 2,
            "proved_libraries": 1,
            "statement_statuses": {"open": 2, "proved": 2},
        },
    }


class FormalVerificationReleaseTest(unittest.TestCase):
    def test_control_output_requires_complete_expected_verdict(self) -> None:
        output = (
            "mutations caught: 13 of 13 kinds\n"
            "positive controls passed: 32 of 32; negative controls refused as "
            "claimed: 7 of 7; mutation controls: caught\n"
            "check.sh: all controls behave\n"
        )
        verdict = CONTROLS.parse_control_output(output)
        self.assertEqual(verdict["positive"], 32)
        self.assertEqual(verdict["negative"], 7)
        self.assertEqual(verdict["mutations_caught"], 13)

    def test_control_output_rejects_partial_verdict(self) -> None:
        output = (
            "mutations caught: 12 of 13 kinds\n"
            "positive controls passed: 32 of 32; negative controls refused as "
            "claimed: 7 of 7; mutation controls: caught\n"
            "check.sh: all controls behave\n"
        )
        with self.assertRaises(CONTROLS.AuditError):
            CONTROLS.parse_control_output(output)

    def test_runtime_audit_requires_digest_pinned_image(self) -> None:
        digest = "a" * 64
        self.assertEqual(
            RUNTIME.expected_image_id(f"registry.test/checker@sha256:{digest}"),
            f"sha256:{digest}",
        )
        with self.assertRaises(RUNTIME.AuditError):
            RUNTIME.expected_image_id("registry.test/checker:latest")

    def test_release_audit_checks_identity_and_relations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            pin = write_fixture(source)
            report = AUDIT.audit(source, pin)
        self.assertEqual(report["counts"]["statements"], 4)
        self.assertEqual(report["checks"]["proof_statement_consistency"], "pass")

    def test_release_audit_rejects_mutated_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            pin = write_fixture(source)
            with (source / "index/statements.tsv").open("a", encoding="utf-8") as stream:
                stream.write("mutated\n")
            with self.assertRaises(AUDIT.AuditError):
                AUDIT.audit(source, pin)

    def test_panel_is_deterministic_and_groups_related_statements(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            pin = write_fixture(source)
            first = PANEL.build_panel(source, pin, groups=1)
            second = PANEL.build_panel(source, pin, groups=1)
        self.assertEqual(first, second)
        self.assertEqual(first["selection"]["eligible_groups"], 2)
        self.assertEqual(len(first["groups"]), 1)
        self.assertEqual(len(first["groups"][0]["open_statements"]), 1)
        self.assertEqual(len(first["groups"][0]["proved_oracles"]), 1)


if __name__ == "__main__":
    unittest.main()
