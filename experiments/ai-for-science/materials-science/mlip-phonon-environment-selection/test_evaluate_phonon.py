import importlib.util
from pathlib import Path

import numpy as np
import pytest


pytest.importorskip("phonopy")


SCRIPT = Path(__file__).parent / "evaluate_phonon.py"
SPEC = importlib.util.spec_from_file_location("evaluate_phonon", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_stability_rule_matches_released_thresholds():
    stable = np.array([[0.0, 0.0, 0.0, 1.0], [0.2, 0.3, 0.4, 1.1]])
    assert MODULE.is_stable(stable)

    optical_instability = stable.copy()
    optical_instability[0, 3] = -0.01
    assert not MODULE.is_stable(optical_instability)

    non_gamma_instability = stable.copy()
    non_gamma_instability[1, 0] = -0.01
    assert not MODULE.is_stable(non_gamma_instability)

    tolerated_acoustic = stable.copy()
    tolerated_acoustic[0, 0] = -34.9 / 47.992
    assert MODULE.is_stable(tolerated_acoustic)

    rejected_acoustic = stable.copy()
    rejected_acoustic[0, 0] = -35.1 / 47.992
    assert not MODULE.is_stable(rejected_acoustic)
