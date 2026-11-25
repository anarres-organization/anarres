import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
FORMAL_SRC = ROOT / "data/formal-verification/vero/src"
sys.path.insert(0, str(FORMAL_SRC))

from anarres_formal_adapter import evidence_report  # noqa: E402

CLI_PATH = FORMAL_SRC / "anarres_formal_adapter/cli.py"
CLI_SPEC = importlib.util.spec_from_file_location("anarres_formal_cli_evidence", CLI_PATH)
assert CLI_SPEC is not None and CLI_SPEC.loader is not None
CLI = importlib.util.module_from_spec(CLI_SPEC)
CLI_SPEC.loader.exec_module(CLI)

EVIDENCE = ROOT / "experiments/cyber/formal-verification/public-evidence"


class VeroPublicEvidenceAdapterTest(unittest.TestCase):
    def test_descriptor_declares_the_evidence_report_capability(self) -> None:
        descriptor = CLI.adapter_descriptor()
        self.assertEqual(descriptor["capabilities"], sorted(set(descriptor["capabilities"])))
        self.assertIn("evidence-report", descriptor["capabilities"])

    def test_report_verifies_the_released_summary_byte_for_byte(self) -> None:
        report = CLI.command_evidence(argparse.Namespace(repository=ROOT))
        self.assertEqual(report["status"], "verified")
        self.assertTrue(report["summary_verified_by_manifest"])
        serialized = evidence_report.canonical_json(report["summary"])
        self.assertEqual(serialized, (EVIDENCE / "results/summary.json").read_text())
        self.assertEqual(
            report["summary_digest"],
            evidence_report.digest(EVIDENCE / "results/summary.json"),
        )

    def test_two_consecutive_runs_are_canonically_equal(self) -> None:
        first = evidence_report.canonical_json(
            CLI.command_evidence(argparse.Namespace(repository=ROOT))
        )
        second = evidence_report.canonical_json(
            CLI.command_evidence(argparse.Namespace(repository=ROOT))
        )
        self.assertEqual(first, second)

    def test_every_summary_section_keeps_its_evidence_class(self) -> None:
        report = CLI.command_evidence(argparse.Namespace(repository=ROOT))
        sections = {key for key in report["summary"] if key != "artifact"}
        records = {record["summary_key"] for record in report["records"]}
        self.assertEqual(records, sections)
        for record in report["records"]:
            self.assertIn(record["timing"], evidence_report.EVIDENCE_TIMING)
            self.assertIn(record["kind"], evidence_report.EVIDENCE_KINDS)
            self.assertEqual(record["outcome"], report["summary"][record["summary_key"]])
        self.assertIn(
            "falsification",
            {record["kind"] for record in report["records"]},
            "the Re:Form falsification must stay visible",
        )

    def test_every_record_carries_source_revisions_and_artifact_digests(self) -> None:
        report = CLI.command_evidence(argparse.Namespace(repository=ROOT))
        for record in report["records"]:
            self.assertTrue(record["sources"])
            for source in record["sources"]:
                self.assertTrue(source["revision"] or source["release_date"])
                for artifact in source["upstream_artifacts"]:
                    self.assertRegex(artifact["sha256"], r"^sha256:[0-9a-f]{64}$")

    def test_report_does_not_create_a_profile_or_authorize_training(self) -> None:
        boundaries = CLI.command_evidence(argparse.Namespace(repository=ROOT))["boundaries"]
        self.assertFalse(boundaries["creates_environment_profile"])
        self.assertFalse(boundaries["ranks_candidates"])
        self.assertFalse(boundaries["authorizes_training"])
        self.assertFalse(boundaries["contains_prospective_forecast"])
        self.assertFalse(boundaries["pools_scores_across_sources"])


class VeroPublicEvidenceTamperTest(unittest.TestCase):
    def checkout(self) -> Path:
        directory = tempfile.TemporaryDirectory(prefix="anarres-public-evidence-")
        self.addCleanup(directory.cleanup)
        target = Path(directory.name) / evidence_report.PUBLIC_EVIDENCE
        shutil.copytree(EVIDENCE, target)
        return Path(directory.name)

    def test_crlf_checkout_still_verifies(self) -> None:
        repository = self.checkout()
        root = repository / evidence_report.PUBLIC_EVIDENCE
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".json", ".py", ".sha256"}:
                path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        report = evidence_report.build_report(repository)
        self.assertEqual(report["manifest"]["files_verified"], 12)

    def test_altered_compact_record_fails_verification(self) -> None:
        repository = self.checkout()
        path = repository / evidence_report.PUBLIC_EVIDENCE / "data/reform.json"
        record = json.loads(path.read_text())
        record["panels"][0]["arms"]["verification_reward"]["spec_superiority"] = 5
        path.write_text(json.dumps(record, indent=2) + "\n")
        with self.assertRaises(evidence_report.EvidenceReportError):
            evidence_report.build_report(repository)

    def test_manifest_rejects_externally_resolved_file_with_valid_digest(self) -> None:
        repository = self.checkout()
        root = repository / evidence_report.PUBLIC_EVIDENCE
        outside = repository / "outside-evidence.txt"
        outside.write_text("not part of the released evidence\n")
        relative = "../../../../outside-evidence.txt"
        self.assertEqual((root / relative).resolve(), outside.resolve())
        manifest = root / evidence_report.MANIFEST
        h = hashlib.sha256(outside.read_bytes()).hexdigest()
        manifest.write_text(manifest.read_text() + f"{h}  {relative}\n")
        altered_digest = evidence_report.release_digest(manifest)
        with (
            mock.patch.object(evidence_report, "TRUSTED_MANIFEST_SHA256", altered_digest),
            self.assertRaisesRegex(evidence_report.EvidenceReportError, "escapes"),
        ):
            evidence_report.verify_manifest(root)

    def test_manifest_rejects_duplicate_normalized_name(self) -> None:
        repository = self.checkout()
        root = repository / evidence_report.PUBLIC_EVIDENCE
        manifest = root / evidence_report.MANIFEST
        original = manifest.read_text()
        first = original.splitlines()[0]
        digest, relative = first.split("  ", 1)
        alias = relative.removeprefix("./") if relative.startswith("./") else "./" + relative
        self.assertNotEqual(alias, relative)
        manifest.write_text(original + f"{digest}  {alias}\n")
        altered_digest = evidence_report.release_digest(manifest)
        with (
            mock.patch.object(evidence_report, "TRUSTED_MANIFEST_SHA256", altered_digest),
            self.assertRaisesRegex(evidence_report.EvidenceReportError, "duplicate"),
        ):
            evidence_report.verify_manifest(root)

    def test_sources_reject_fake_forty_character_revision(self) -> None:
        repository = self.checkout()
        root = repository / evidence_report.PUBLIC_EVIDENCE
        path = root / evidence_report.SOURCES
        data = json.loads(path.read_text())
        with_revision = next(x for x in data["sources"] if x.get("revision"))
        with_revision["revision"] = "z" * 40
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(evidence_report.EvidenceReportError, "revision"):
            evidence_report.load_sources(root)

    def test_sources_reject_duplicate_source_names(self) -> None:
        repository = self.checkout()
        root = repository / evidence_report.PUBLIC_EVIDENCE
        path = root / evidence_report.SOURCES
        data = json.loads(path.read_text())
        data["sources"].append(dict(data["sources"][0]))
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(evidence_report.EvidenceReportError, "duplicate"):
            evidence_report.load_sources(root)

    def test_altered_manifest_digest_fails_verification(self) -> None:
        repository = self.checkout()
        path = repository / evidence_report.PUBLIC_EVIDENCE / "MANIFEST.sha256"
        lines = path.read_text().splitlines()
        lines[0] = "0" * 64 + "  ./README.md"
        path.write_text("\n".join(lines) + "\n")
        with self.assertRaises(evidence_report.EvidenceReportError):
            evidence_report.build_report(repository)

    def test_checkout_reproducer_is_never_executed(self) -> None:
        repository = self.checkout()
        root = repository / evidence_report.PUBLIC_EVIDENCE
        marker = repository / "executed.txt"
        reproducer = root / evidence_report.REPRODUCER
        reproducer.write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n"
        )
        manifest = root / evidence_report.MANIFEST
        lines = manifest.read_text().splitlines()
        digest = evidence_report.release_digest(reproducer)
        lines = [
            f"{digest}  {name}" if Path(name).as_posix() == evidence_report.REPRODUCER else line
            for line in lines
            for _, separator, name in [line.partition("  ")]
            if separator
        ]
        manifest.write_text("\n".join(lines) + "\n")
        with self.assertRaisesRegex(evidence_report.EvidenceReportError, "trusted release"):
            evidence_report.build_report(repository)
        self.assertFalse(marker.exists())

    def test_edited_summary_fails_verification(self) -> None:
        repository = self.checkout()
        path = repository / evidence_report.PUBLIC_EVIDENCE / "results/summary.json"
        summary = json.loads(path.read_text())
        summary["vericoding"]["mixed_success_tasks"] += 1
        path.write_text(evidence_report.canonical_json(summary))
        with self.assertRaises(evidence_report.EvidenceReportError):
            evidence_report.build_report(repository)


if __name__ == "__main__":
    unittest.main()
