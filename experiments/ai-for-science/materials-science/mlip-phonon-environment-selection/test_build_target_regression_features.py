import importlib.util
from collections import Counter
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).with_name("build_target_regression_features.py")
SPEC = importlib.util.spec_from_file_location("build_target_regression_features", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_formula_and_similarity_features_are_well_defined():
    assert MODULE.formula_counts("Li2FeSiO4") == Counter({"Li": 2, "Fe": 1, "Si": 1, "O": 4})
    assert MODULE.formula_counts("Cs3 H4 Se1") == Counter({"Cs": 3, "H": 4, "Se": 1})
    assert MODULE.jaccard({"Li", "O"}, {"Li", "Fe", "O"}) == pytest.approx(2 / 3)
    assert MODULE.distribution_overlap(
        Counter({"Li": 2, "O": 1}), Counter({"Li": 1, "O": 1})
    ) == pytest.approx(5 / 6)


def test_formula_parser_rejects_unconsumed_text():
    with pytest.raises(ValueError):
        MODULE.formula_counts("Li2(O)")
