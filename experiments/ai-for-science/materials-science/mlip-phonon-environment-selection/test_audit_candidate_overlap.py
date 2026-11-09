import bz2
import importlib.util
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent / "audit_candidate_overlap.py"
SPEC = importlib.util.spec_from_file_location("audit_candidate_overlap", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_reduced_formula_is_order_invariant():
    assert MODULE.parse_reduced_formula("Ta1 Cu1 Re1") == (
        ("Cu", 1),
        ("Re", 1),
        ("Ta", 1),
    )
    assert MODULE.parse_reduced_formula("O4 Si2") == (("O", 2), ("Si", 1))


def test_parent_space_group_parsing():
    assert MODULE.parse_parent_space_group("agm004242068_ABC_0_spg216") == 216


def test_descriptor_text_is_stable():
    descriptor = ((("O", 2), ("Si", 1)), 136)
    assert MODULE.descriptor_text(descriptor) == "O2Si1|spg136"


def test_atomic_number_spec_supports_ranges():
    assert MODULE.parse_atomic_number_spec("1-3,5,8-9") == {1, 2, 3, 5, 8, 9}


def test_target_descriptor_streams_identity_fields():
    document = """displacements:
- atom: 1
primitive_cell:
  lattice:
  - - 1
  points:
  - coordinates:
    - 0
    mass: 16
    symbol: O
  - coordinates:
    - 0.5
    mass: 16
    symbol: O
  - coordinates:
    - 0.25
    mass: 28
    symbol: Si
  reciprocal_lattice:
  - - 1
space_group:
  Hall_symbol: x
  number: 136
supercell:
"""
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "target.yaml.bz2"
        with bz2.open(path, "wt", encoding="utf-8") as handle:
            handle.write(document)
        assert MODULE.target_descriptor(path) == ((("O", 2), ("Si", 1)), 136)
