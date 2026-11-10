import importlib.util
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "target_fixture_audit", ROOT / "scripts" / "audit_target_fixtures.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


PDB = "ATOM      1  CA  ALA A   1      10.000  11.000  12.000  1.00 20.00           C  \n"
SDF = "ligand\n  test\n\n  0  0  0  0  0  0  0  0  0  0  1 V2000\nM  END\n$$$$\n"


def fixture_inputs(tmp_path: Path, duplicate: bool = False):
    archive = tmp_path / "fixtures.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("root/P12345/P12345_prep.pdb", PDB)
        handle.writestr("root/P12345/P12345_pocket10.pdb", PDB)
        handle.writestr("root/P12345/P12345_lig.sdf", SDF)
        handle.writestr("root/P12345/results/outcome.csv", "sealed")
        if duplicate:
            handle.writestr("copy/P12345/P12345_lig.sdf", SDF)
    archive_audit = {"archive": {"sha256": "a" * 64, "size_bytes": archive.stat().st_size}}
    panel = {
        "archive_sha256": "a" * 64,
        "panel_size": 1,
        "target_ids": ["P12345"],
        "target_ids_sha256": "b" * 64,
        "outcomes_inspected": False,
    }
    return archive, archive_audit, panel


def test_fixture_audit_reads_only_selected_triplet(tmp_path: Path) -> None:
    archive, archive_audit, panel = fixture_inputs(tmp_path)
    result = MODULE.audit(archive, archive_audit, panel)
    assert result["targets"][0]["fixture_integrity"] == "pass"
    assert result["sealed_boundary"]["opened_fixture_files"] == 3
    assert result["sealed_boundary"]["outcome_file_contents_read"] is False


def test_fixture_audit_rejects_duplicate_fixture(tmp_path: Path) -> None:
    archive, archive_audit, panel = fixture_inputs(tmp_path, duplicate=True)
    with pytest.raises(ValueError, match="duplicate lig fixture"):
        MODULE.audit(archive, archive_audit, panel)


def test_pdb_rejects_missing_coordinates() -> None:
    with pytest.raises(ValueError, match="no coordinate records"):
        MODULE.audit_pdb(b"HEADER only\n")
