import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parent / "construct_candidate_bank.py"
SPEC = importlib.util.spec_from_file_location("construct_candidate_bank", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_formula_elements_and_exact_atom_selection():
    assert MODULE.elements_from_formula("Cr1 Te1 Mo2") == {"Cr", "Te", "Mo"}
    records = []
    for index in range(500):
        records.append(
            {
                "record_index": index,
                "parent_id": f"parent-{index}",
                "natoms": 3 + index % 7,
                "hash_score": f"{index:064x}",
                "signal_density": float(index % 31),
                "coverage_score": float(index % 29),
                "target_affinity": float(index % 23) / 23,
                "hybrid_score": float(index % 19),
            }
        )
    for rule in MODULE.SELECTION_RULES:
        selected = MODULE.select_equal_atoms(records, rule, 2_000)
        assert sum(row["natoms"] for row in selected) == 2_000
        assert len({row["parent_id"] for row in selected}) == len(selected)
