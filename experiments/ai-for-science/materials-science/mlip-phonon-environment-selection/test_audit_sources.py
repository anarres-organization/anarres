import importlib.util
import io
import json
import tarfile
from pathlib import Path


SCRIPT = Path(__file__).parent / "audit_sources.py"
SPEC = importlib.util.spec_from_file_location("mlip_source_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_first_header_accepts_required_extxyz_schema(tmp_path):
    archive = tmp_path / "sample.tar.gz"
    payload = (
        "2\n"
        'Lattice="1 0 0 0 1 0 0 0 1" '
        "Properties=species:S:1:pos:R:3:forces:R:3 "
        'energy=-1.0 stress="0 0 0 0 0 0 0 0 0" pbc="T T T"\n'
        "H 0 0 0 0 0 0\nH 0 0 0.5 0 0 0\n"
    ).encode()
    with tarfile.open(archive, "w:gz") as handle:
        info = tarfile.TarInfo("disp_struct/mp-test/disp_000.extxyz")
        info.size = len(payload)
        handle.addfile(info, io.BytesIO(payload))
    with tarfile.open(archive, "r:gz") as handle:
        result = MODULE.first_header(handle, handle.getmembers()[0])
    assert result["atom_count"] == 2
    assert all(result["required_fields"].values())


def test_public_constants_match_qualified_artifact_if_present():
    path = Path(__file__).parent / "SOURCE_QUALIFICATION.json"
    if not path.exists():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "qualified"
    assert payload["construction_reservoir"]["archive"]["sha256"] == MODULE.OMAT_ARCHIVE_SHA256
    assert payload["physical_target"]["metadata"]["sha256"] == MODULE.PBE_CSV_SHA256
    assert payload["physical_target"]["displacements"]["sha256"] == MODULE.ALEXANDRIA_ARCHIVE_SHA256
