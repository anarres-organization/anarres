from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    CONTRACT_PATH,
    canonical_json_bytes,
    contract_hashes,
    load_json,
    sha256_path,
    unit_name,
    verify_source,
)


def gate(source_dir: Path, unit_dir: Path) -> dict[str, object]:
    contract = load_json(CONTRACT_PATH)
    expected_hashes = contract_hashes()
    records: list[dict[str, object]] = []
    for assay in contract["candidate_assays"]:
        verify_source(source_dir, assay)
        for strategy in sorted(contract["strategies"]):
            for seed in contract["seeds"]:
                path = unit_dir / unit_name(assay, strategy, seed)
                if not path.is_file():
                    raise FileNotFoundError(path)
                unit = load_json(path)
                if unit["status"] != "OUTCOME_BEARING__DO_NOT_OPEN_BEFORE_COMPLETE_GATE":
                    raise ValueError(f"unexpected unit status: {path}")
                if unit["identity"] != {"assay": assay, "strategy": strategy, "seed": seed}:
                    raise ValueError(f"unit identity mismatch: {path}")
                if unit["contract_hashes"] != expected_hashes:
                    raise ValueError(f"unit contract mismatch: {path}")
                records.append(
                    {
                        "assay": assay,
                        "strategy": strategy,
                        "seed": seed,
                        "filename": path.name,
                        "sha256": sha256_path(path),
                    }
                )
    if len(records) != contract["release_gate"]["expected_units"]:
        raise ValueError("unexpected unit count")
    return {
        "schema_version": 1,
        "study_id": contract["study_id"],
        "status": "RELEASE_GATE_PASSED__OUTCOMES_MAY_BE_OPENED",
        "contract_hashes": expected_hashes,
        "unit_count": len(records),
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--unit-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = gate(args.source_dir, args.unit_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(result))
    print(args.output)


if __name__ == "__main__":
    main()
