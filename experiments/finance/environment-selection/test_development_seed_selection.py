#!/usr/bin/env python3

import importlib.util
import json
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "select_development_seeds.py"
SPEC = importlib.util.spec_from_file_location("select_development_seeds", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_oracle_matrix_requires_all_workflows() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "summary.json"
        rows = [{"task": workflow, "passed": True, "error": None} for workflow in MODULE.WORKFLOWS]
        path.write_text(json.dumps(rows))
        assert MODULE.oracle_matrix_passes(path) is True
        rows[0]["passed"] = False
        path.write_text(json.dumps(rows))
        assert MODULE.oracle_matrix_passes(path) is False


if __name__ == "__main__":
    test_oracle_matrix_requires_all_workflows()
