import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "molgenbench_archive_audit",
    ROOT / "scripts" / "audit_molgenbench_archive.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def build_archive(tmp_path: Path, unsafe: bool = False) -> tuple[Path, Path]:
    archive = tmp_path / "MolGenBench_Version4.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        for suffix in ("prep.pdb", "pocket10.pdb", "lig.sdf"):
            handle.writestr(f"dataset/P12345/P12345_{suffix}", "fixture")
        handle.writestr(
            "dataset/P12345/Round1/De_novo_Results/model/results/value.csv",
            "sealed outcome",
        )
        if unsafe:
            handle.writestr("../escape.txt", "unsafe")
    registry = {
        "study": "test",
        "molgenbench": {
            "dataset": {
                "archive_size_bytes": archive.stat().st_size,
                "published_md5": hashlib.md5(
                    archive.read_bytes(), usedforsecurity=False
                ).hexdigest(),
            }
        },
    }
    sources = tmp_path / "SOURCES.json"
    sources.write_text(json.dumps(registry), encoding="utf-8")
    return archive, sources


def test_archive_audit_reads_metadata_without_outcomes(tmp_path: Path) -> None:
    archive, sources = build_archive(tmp_path)
    result = MODULE.audit(archive, sources)
    assert result["target_fixtures"]["target_ids"] == ["P12345"]
    assert result["sealed_boundary"]["outcome_members_present"] == 1
    assert not result["sealed_boundary"]["outcome_file_contents_read"]


def test_archive_audit_rejects_unsafe_member(tmp_path: Path) -> None:
    archive, sources = build_archive(tmp_path, unsafe=True)
    with pytest.raises(ValueError, match="unsafe member paths"):
        MODULE.audit(archive, sources)
