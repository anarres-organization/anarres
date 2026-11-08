import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "reaction_source_audit", ROOT / "scripts" / "audit_source.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_count_reactions(tmp_path: Path) -> None:
    fixture = tmp_path / "reaction.yaml"
    fixture.write_text(
        "UniReaction:\n"
        "  first:\n"
        "    forward: a\n"
        "  second:\n"
        "    forward: b\n"
        "BiReaction:\n"
        "  third:\n"
        "    forward: c\n",
        encoding="utf-8",
    )
    assert MODULE.count_reactions(fixture, "UniReaction") == 2
    assert MODULE.count_reactions(fixture, "BiReaction") == 1


def test_verify_files_detects_hash_change(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.txt"
    fixture.write_text("qualified\n", encoding="utf-8")
    observed = MODULE.sha256(fixture)
    assert MODULE.verify_files(tmp_path, {"fixture.txt": observed}) == {"fixture.txt": observed}
    with pytest.raises(ValueError, match="hashes differ"):
        MODULE.verify_files(tmp_path, {"fixture.txt": "0" * 64})


def test_verify_files_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Missing qualified files"):
        MODULE.verify_files(tmp_path, {"missing.txt": "0" * 64})
