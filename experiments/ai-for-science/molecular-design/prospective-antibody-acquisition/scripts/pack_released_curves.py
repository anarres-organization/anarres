from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import canonical_json_bytes, load_json, sha256_path  # noqa: E402


def pack(unit_dir: Path, release_gate_path: Path) -> dict[str, object]:
    gate = load_json(release_gate_path)
    if gate["status"] != "RELEASE_GATE_PASSED__OUTCOMES_MAY_BE_OPENED":
        raise ValueError("release gate has not passed")
    curves: list[dict[str, object]] = []
    for record in gate["records"]:
        path = unit_dir / record["filename"]
        if sha256_path(path) != record["sha256"]:
            raise ValueError(f"unit changed after release gate: {path}")
        unit = load_json(path)
        curves.append(
            {
                "identity": unit["identity"],
                "observed_counts": unit["budget"]["observed_counts"],
                "final_fraction": unit["budget"]["final_fraction"],
                "top_count": unit["outcome"]["top_count"],
                "recall_curve": unit["outcome"]["recall_curve"],
                "normalized_curve_auc": unit["outcome"]["normalized_curve_auc"],
                "endpoint_recall": unit["outcome"]["endpoint_recall"],
                "selection_sha256_by_batch": unit["selection_sha256_by_batch"],
                "unit_sha256": record["sha256"],
            }
        )
    return {
        "schema_version": 1,
        "study_id": gate["study_id"],
        "status": "RELEASED_AFTER_COMPLETE_MATRIX_GATE",
        "release_gate_sha256": sha256_path(release_gate_path),
        "curve_count": len(curves),
        "curves": curves,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit-dir", type=Path, required=True)
    parser.add_argument("--release-gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = pack(args.unit_dir, args.release_gate)
    args.output.write_bytes(canonical_json_bytes(result))
    print(args.output)


if __name__ == "__main__":
    main()
