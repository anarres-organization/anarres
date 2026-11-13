from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
        "study_id": "prospective_protein_acquisition_v1",
        "status": "PROTOCOL_FROZEN__OUTCOMES_UNOPENED",
        "files": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths},
    }
    (ROOT / "FREEZE.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
