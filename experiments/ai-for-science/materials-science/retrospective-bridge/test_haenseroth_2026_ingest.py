import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "ingest_haenseroth_2026.py"
SPEC = importlib.util.spec_from_file_location("haenseroth_ingest", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_reconstructs_generator_panels(tmp_path):
    members = []
    for system_index, system in enumerate(MODULE.SYSTEMS):
        for generator_index, generator in enumerate(MODULE.GENERATORS):
            relative = f"{generator}/{system}/errors.txt"
            path = tmp_path / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            force = 0.02 + generator_index * 0.01 + system_index * 0.001
            energy = 0.002 + generator_index * 0.001
            path.write_text(
                f"Mean absolute force error: {force} eV/Angstrom\n"
                f"Mean relative force error: {force + 0.001}\n"
                f"Mean absolute energy error per atom: {energy} eV/atom\n",
                encoding="utf-8",
            )
            members.append(
                {
                    "relative_path": relative,
                    "archive_member": f"archive/{relative}",
                    "crc32": "00000000",
                }
            )
    (tmp_path / "FETCH_MANIFEST.json").write_text(
        json.dumps(
            {
                "artifact": "haenseroth_2026_selective_fetch_v1",
                "archive_url": "https://example.invalid/archive.zip",
                "archive_md5_from_zenodo": "0" * 32,
                "archive_size_bytes": 123,
                "members": members,
            }
        ),
        encoding="utf-8",
    )

    payload = MODULE.reconstruct(tmp_path)
    assert payload["panel_count"] == 7
    assert payload["arm_count"] == 21
    cdp = [arm for arm in payload["arms"] if arm["material_system"] == "cdp"]
    assert sum(arm["outcome"]["joint_threshold_pass"] for arm in cdp) == 3
    best = max(cdp, key=lambda arm: arm["derived"]["panel_normalized_joint_utility"])
    assert best["generator"] == "grace_oam"
