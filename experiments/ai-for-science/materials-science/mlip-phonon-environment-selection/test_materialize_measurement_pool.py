import importlib.util
import json
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent / "materialize_measurement_pool.py"
SPEC = importlib.util.spec_from_file_location("materialize_measurement_pool", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_selected_rows_takes_equal_family_prefixes():
    rows = [
        {"source_family": family, "value": value} for family in ("a", "b") for value in range(3)
    ]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "manifest.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        selected = MODULE.selected_rows(path, 2)
    assert [(row["source_family"], row["value"]) for row in selected] == [
        ("a", 0),
        ("a", 1),
        ("b", 0),
        ("b", 1),
    ]


def test_selected_rows_rejects_missing_and_nonpositive_requests():
    rows = [{"source_family": "a", "value": value} for value in range(2)]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "manifest.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        for request in (0, -1, 3):
            try:
                MODULE.selected_rows(path, request)
            except (ValueError, RuntimeError):
                pass
            else:
                raise AssertionError(f"request {request} should fail")


if __name__ == "__main__":
    test_selected_rows_takes_equal_family_prefixes()
    test_selected_rows_rejects_missing_and_nonpositive_requests()
