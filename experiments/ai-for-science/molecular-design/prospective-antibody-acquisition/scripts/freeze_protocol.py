from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    paths = [
        "FROZEN_CONTRACT.json",
        "SOURCES.json",
        "scripts/common.py",
        "scripts/run_unit.py",
        "scripts/gate_complete_panel.py",
        "scripts/score_panel.py",
    ]
    result = {
        "schema_version": 1,
        "study_id": "prospective_antibody_acquisition_v1",
        "status": "PROTOCOL_FROZEN__OUTCOMES_UNOPENED",
        "files": {path: sha256(ROOT / path) for path in paths},
    }
    (ROOT / "FREEZE.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
