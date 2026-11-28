#!/usr/bin/env python3
"""Score d512 mixture directions against the released larger Grug ladder."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASELINES = HERE / "GRUG_SWARM_BASELINE_RESULTS.json"
SOURCE = HERE / "GRUG_SCALE_TRANSFER_SOURCE.json"
RESULTS = HERE / "GRUG_SCALE_TRANSFER_RESULTS.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    baselines = json.loads(BASELINES.read_text())
    source = json.loads(SOURCE.read_text())
    directions = baselines["published_selected_pair"]["hellinger_rbf_kernel"][
        "held_out_loss_or_bpb"
    ]["directions"]
    scale_results = {}
    for scale, outcomes in source["scales"].items():
        actual = {subset: "improved" for subset in outcomes["improved"]}
        actual.update({subset: "regressed" for subset in outcomes["regressed"]})
        if set(actual) != set(source["subsets"]):
            raise ValueError(f"incomplete subset outcomes at {scale}")
        rows = []
        for subset in source["subsets"]:
            target = f"eval_dropless/paloma/{subset}-llama3/bpb"
            d512 = directions[target]
            rows.append(
                {
                    "subset": subset,
                    "d512_observed": d512["observed"],
                    "d512_surrogate": d512["predicted"],
                    "larger_scale_observed": actual[subset],
                }
            )
        scale_results[scale] = {
            "subsets": len(rows),
            "larger_scale_improvements": len(outcomes["improved"]),
            "d512_observed_direction_transfer_accuracy": sum(
                row["d512_observed"] == row["larger_scale_observed"] for row in rows
            )
            / len(rows),
            "d512_surrogate_direction_transfer_accuracy": sum(
                row["d512_surrogate"] == row["larger_scale_observed"] for row in rows
            )
            / len(rows),
            "macro_bpb": {
                "original": outcomes["macro_original_bpb"],
                "selected": outcomes["macro_selected_bpb"],
            },
            "directions": rows,
        }
    return {
        "artifact": "anarres_grug_mixture_scale_transfer_stress_test_v1",
        "status": "retrospective development stress test; not a prospective result",
        "inputs": {
            "d512_baselines_sha256": digest(BASELINES),
            "scale_source_sha256": digest(SOURCE),
        },
        "model": "d512 Hellinger-RBF surrogate with both published lineages excluded from fitting",
        "results": scale_results,
        "boundary": source["contract_difference"],
        "interpretation": (
            "Direction transfer improves with model width, but the d512 and larger-scale "
            "schedules differ. The result motivates an identical-contract scale panel; it "
            "does not establish a pretraining scaling law or post-training transfer."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build()
    if args.check:
        if json.loads(RESULTS.read_text()) != expected:
            raise SystemExit("stale Grug scale-transfer result")
        return
    RESULTS.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
