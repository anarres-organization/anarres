#!/usr/bin/env python3
"""Verify a complete molecular training matrix before endpoint evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "MATCHED_TRAINING_EVALUATION_CONTRACT_V1.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def count_jsonl(path: Path) -> int:
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def verify_hashed_file(path: Path, expected: str, label: str) -> str:
    if not path.is_file() or sha256_file(path) != expected:
        raise ValueError(f"{label} is missing or has the wrong hash")
    return expected


def panel_arms(contract: dict[str, Any], panel_kind: str) -> list[str]:
    if panel_kind == "development":
        return list(contract["development_panel"]["arms"])
    if panel_kind == "prospective":
        return list(contract["development_panel"]["prospective_banks_excluded"])
    raise ValueError(f"unsupported panel kind: {panel_kind}")


def gate_training_matrix(
    contract_path: Path,
    runs_root: Path,
    panel_kind: str = "development",
    forecast_freeze: Path | None = None,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    training = contract["training"]
    arms = panel_arms(contract, panel_kind)
    expected = {(arm, seed) for arm in arms for seed in training["seeds"]}
    if panel_kind == "prospective" and forecast_freeze is None:
        raise ValueError("prospective training requires the frozen forecast")
    freeze_sha256 = sha256_file(forecast_freeze) if forecast_freeze is not None else None
    records: list[dict[str, Any]] = []
    checkpoint_hashes: set[str] = set()
    contract_sha256 = sha256_file(contract_path)
    for arm, seed in sorted(expected):
        run = runs_root / f"{arm}-{seed}"
        manifest_path = run / "MATCHED_TRAINING_RUN.json"
        if not manifest_path.is_file():
            raise ValueError(f"training run is incomplete: {arm}-{seed}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        checks = manifest.get("checks")
        if (
            manifest.get("study") != contract["study"]
            or manifest.get("contract") != contract["contract"]
            or manifest.get("status") != "complete"
            or manifest.get("arm") != arm
            or manifest.get("seed") != seed
            or manifest.get("initial_step") != 0
            or manifest.get("final_step") != training["maximum_updates"]
            or not isinstance(checks, dict)
            or not checks
            or not all(checks.values())
        ):
            raise ValueError(f"training manifest differs from the contract: {arm}-{seed}")
        artifacts = manifest.get("artifact_sha256", {})
        if artifacts.get("contract") != contract_sha256:
            raise ValueError(f"training manifest binds a different contract: {arm}-{seed}")
        if panel_kind == "prospective" and (
            manifest.get("panel_kind") != "prospective"
            or artifacts.get("prospective_freeze") != freeze_sha256
        ):
            raise ValueError(f"prospective run is not bound to the frozen forecast: {arm}-{seed}")
        verify_hashed_file(run / "training.jsonl", artifacts["training_log"], "training log")
        verify_hashed_file(run / "sample.jsonl", artifacts["online_samples"], "online samples")
        if count_jsonl(run / "training.jsonl") != training["maximum_updates"]:
            raise ValueError(f"training log has the wrong number of updates: {arm}-{seed}")
        expected_samples = training["maximum_updates"] * training["online_trajectories_per_update"]
        if count_jsonl(run / "sample.jsonl") != expected_samples:
            raise ValueError(f"online sample log has the wrong size: {arm}-{seed}")

        checkpoints: dict[str, str] = {}
        expected_checkpoint_hashes = artifacts.get("required_checkpoints", {})
        if set(expected_checkpoint_hashes) != {
            str(step) for step in training["checkpoint_updates"]
        }:
            raise ValueError(f"checkpoint inventory differs from the contract: {arm}-{seed}")
        for step in training["checkpoint_updates"]:
            checkpoint = run / "checkpoints" / f"step_{step:06d}.ckpt"
            digest = verify_hashed_file(
                checkpoint,
                expected_checkpoint_hashes[str(step)],
                f"checkpoint {arm}-{seed}-{step}",
            )
            checkpoints[str(step)] = digest
            checkpoint_hashes.add(digest)
        records.append(
            {
                "arm": arm,
                "seed": seed,
                "manifest_sha256": sha256_file(manifest_path),
                "replay_items_sha256": manifest["replay"]["items_sha256"],
                "checkpoints": checkpoints,
            }
        )
    expected_checkpoint_count = len(expected) * len(training["checkpoint_updates"])
    if len(checkpoint_hashes) != expected_checkpoint_count:
        raise ValueError(f"{panel_kind} runs do not have distinct checkpoint artifacts")
    prospective = panel_kind == "prospective"
    return {
        "schema_version": f"anarres.molecular-{panel_kind}-training-gate.v1",
        "study": contract["study"],
        "contract": contract["contract"],
        "status": f"{panel_kind.upper()}_TRAINING_COMPLETE__ENDPOINT_OUTCOMES_UNOPENED",
        "panel_kind": panel_kind,
        "endpoint_outcomes_opened": False,
        "contract_sha256": contract_sha256,
        "prospective_freeze_sha256": freeze_sha256 if prospective else None,
        "run_count": len(records),
        "checkpoint_count": expected_checkpoint_count,
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument(
        "--panel-kind", choices=("development", "prospective"), default="development"
    )
    parser.add_argument("--forecast-freeze", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.contract.resolve() != DEFAULT_CONTRACT.resolve():
        raise ValueError("claim-bearing gates require the released matched contract")
    if args.output.exists():
        raise FileExistsError(args.output)
    result = gate_training_matrix(
        args.contract,
        args.runs_root,
        panel_kind=args.panel_kind,
        forecast_freeze=args.forecast_freeze,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "run_count": result["run_count"]}, indent=2))


if __name__ == "__main__":
    main()
