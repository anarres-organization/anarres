#!/usr/bin/env python3
"""Build the Kim et al. cross-domain compatibility audit from source data."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SOURCE_ID = "kim_2026_cross_domain_transfer"
DOI = "10.1038/s41467-026-70195-8"
WORKBOOK_SHA256 = "f2dd58b5d4ec9ed6c4467219a109e1c4c1f2d23f45d8a6d03789b6ac00a63ac6"
SUPPLEMENT_SHA256 = "f6474e7d1c3bd5406cae49a751a4d704688edcba6e09fa8d6e47e6313e5d231b"

# Exact values from Source Data sheet ablation_MPSP_MAE, rows 4--14.
# The filled cells in columns A--C encode training-set membership.
ARMS = [
    ("mptrj_only", 1, 0, 0, None, None, 0.056312, None, 0.156852868, None),
    (
        "mptrj_spice_unregularized",
        1,
        1,
        0,
        "unregularized",
        0.0,
        0.057738,
        0.024620,
        0.101268506,
        69526.72852,
    ),
    (
        "mptrj_spice_all_1e-3",
        1,
        1,
        0,
        "all_parameters",
        1e-3,
        0.056155,
        0.024747,
        0.091145560,
        3755.401394,
    ),
    (
        "mptrj_spice_selective_1e-3",
        1,
        1,
        0,
        "task_specific_parameters",
        1e-3,
        0.058533,
        0.024910,
        0.246398363273152,
        0.010041,
    ),
    (
        "mptrj_spice_selective_1e-4",
        1,
        1,
        0,
        "task_specific_parameters",
        1e-4,
        0.057999,
        0.025075,
        0.0866430059953237,
        0.609331,
    ),
    (
        "mptrj_spice_selective_1e-5",
        1,
        1,
        0,
        "task_specific_parameters",
        1e-5,
        0.057941,
        0.024742,
        0.083644823,
        10.64643,
    ),
    (
        "mptrj_spice_selective_1e-6",
        1,
        1,
        0,
        "task_specific_parameters",
        1e-6,
        0.058309,
        0.025097,
        0.091011908335307,
        171.140305,
    ),
    (
        "mptrj_spice_selective_1e-7",
        1,
        1,
        0,
        "task_specific_parameters",
        1e-7,
        0.057813,
        0.024681,
        0.096073856824110,
        1938.934868,
    ),
    ("mptrj_dbs_only", 1, 0, 1, None, None, 0.056095, None, 0.114416388, None),
    (
        "mptrj_spice_dbs_unregularized",
        1,
        1,
        1,
        "unregularized",
        0.0,
        0.057584,
        0.024866,
        0.068720598,
        67764.5105,
    ),
    (
        "mptrj_spice_dbs_selective_1e-5",
        1,
        1,
        1,
        "task_specific_parameters",
        1e-5,
        0.057890,
        0.025769,
        0.048304002,
        9.937525366,
    ),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ingest(*, workbook: Path | None = None, supplement: Path | None = None) -> dict:
    for path, expected in (
        (workbook, WORKBOOK_SHA256),
        (supplement, SUPPLEMENT_SHA256),
    ):
        if path is not None and sha256(path) != expected:
            raise ValueError(f"checksum mismatch for {path.name}")

    baseline = ARMS[0][8]
    arms = []
    for (
        name,
        mptrj,
        spice,
        dbs,
        regularization,
        weight,
        crystal_gga,
        molecule_hybrid,
        molecule_gga,
        task_specific_l2,
    ) in ARMS:
        arms.append(
            {
                "arm": name,
                "training_set": {
                    "mptrj": mptrj,
                    "spice": spice,
                    "domain_bridging_set": dbs,
                },
                "regularization": {
                    "scope": regularization,
                    "weight": weight,
                },
                "force_mae_eV_per_A": {
                    "crystal_gga": crystal_gga,
                    "molecule_hybrid": molecule_hybrid,
                    "molecule_gga": molecule_gga,
                },
                "task_specific_parameter_l2_norm": task_specific_l2,
                "derived": {
                    "molecule_gga_mae_reduction_vs_mptrj_only_fraction": (baseline - molecule_gga)
                    / baseline
                },
            }
        )

    return {
        "artifact": "kim_2026_cross_domain_compatibility_audit_v1",
        "source_id": SOURCE_ID,
        "doi": DOI,
        "source_sheet": "ablation_MPSP_MAE!A1:I14",
        "arm_count": len(arms),
        "arms": arms,
        "source_files": {
            "41467_2026_70195_MOESM3_ESM.xlsx": {"sha256": WORKBOOK_SHA256},
            "41467_2026_70195_MOESM1_ESM.pdf": {"sha256": SUPPLEMENT_SHA256},
        },
        "interpretation_boundary": [
            "Every numerical value comes from the official Source Data workbook; "
            "no figure is digitized.",
            "The ablation changes database membership and the regularization contract, "
            "so it is not a matched fixed-trainer environment comparison.",
            "The 0.1% domain-bridging set adds PBE relabeling cost that is not matched "
            "across arms.",
            "The source data report one value per arm and do not expose independent "
            "training-seed outcomes for this ablation.",
            "The audit tests how data composition and optimization interact during "
            "cross-domain transfer; it remains outside the fitted bridge.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path)
    parser.add_argument("--supplement", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = ingest(workbook=args.workbook, supplement=args.supplement)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
