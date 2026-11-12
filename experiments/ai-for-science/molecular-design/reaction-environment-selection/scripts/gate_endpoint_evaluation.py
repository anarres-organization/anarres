#!/usr/bin/env python3
"""Verify the complete molecular endpoint matrix before comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "MATCHED_TRAINING_EVALUATION_CONTRACT_V1.json"
DEFAULT_THRESHOLDS = ROOT / "Q07820_REFERENCE_THRESHOLDS_V1.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"{label} is missing")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def panel_name(arm: str, seed: int, step: int) -> str:
    return f"{arm}-{seed}-step{step:06d}"


def panel_arms(contract: dict[str, Any], panel_kind: str) -> list[str]:
    if panel_kind == "development":
        return list(contract["development_panel"]["arms"])
    if panel_kind == "prospective":
        return list(contract["development_panel"]["prospective_banks_excluded"])
    raise ValueError(f"unsupported panel kind: {panel_kind}")


def expected_panels(
    contract: dict[str, Any], panel_kind: str = "development"
) -> list[tuple[str, int, int]]:
    training = contract["training"]
    panels = [("warm_start", seed, 0) for seed in training["seeds"]]
    panels.extend(
        (arm, seed, step)
        for arm in panel_arms(contract, panel_kind)
        for seed in training["seeds"]
        for step in training["checkpoint_updates"]
    )
    return sorted(panels)


def verify_panel(
    panel_dir: Path,
    contract: dict[str, Any],
    contract_sha256: str,
    thresholds_sha256: str,
    arm: str,
    seed: int,
    step: int,
) -> dict[str, Any]:
    attempts = contract["evaluation"]["attempts_per_policy_seed_checkpoint"]
    evaluation_seed = contract["evaluation"]["seeds"][str(seed)][str(step)]
    samples = panel_dir / "samples.jsonl"
    sample_manifest_path = panel_dir / "SAMPLE_MANIFEST.json"
    docking_records = panel_dir / "docking-records.jsonl"
    docking_report_path = panel_dir / "DOCKING_REPORT.json"
    endpoint_records = panel_dir / "endpoint-records.jsonl"
    metrics_report_path = panel_dir / "METRICS_REPORT.json"
    qualifying_report_path = panel_dir / "QUALIFYING_HITS.json"

    sample_manifest = load_object(sample_manifest_path, "sample manifest")
    if (
        sample_manifest.get("study") != contract["study"]
        or sample_manifest.get("contract") != contract["contract"]
        or sample_manifest.get("status") != "complete"
        or sample_manifest.get("arm") != arm
        or sample_manifest.get("training_seed") != seed
        or sample_manifest.get("checkpoint_step") != step
        or sample_manifest.get("evaluation_seed") != evaluation_seed
        or sample_manifest.get("attempts") != attempts
        or sample_manifest.get("artifact_sha256", {}).get("contract") != contract_sha256
        or sample_manifest.get("artifact_sha256", {}).get("samples") != sha256_file(samples)
    ):
        raise ValueError(f"sample identity differs from the contract: {panel_dir.name}")

    docking_report = load_object(docking_report_path, "docking report")
    if (
        docking_report.get("contract") != contract["contract"]
        or docking_report.get("status") != "complete"
        or docking_report.get("sample_seed") != evaluation_seed
        or docking_report.get("attempts") != attempts
        or docking_report.get("infrastructure_failures") != 0
        or docking_report.get("inputs", {}).get("samples_sha256") != sha256_file(samples)
        or docking_report.get("output_records_sha256") != sha256_file(docking_records)
    ):
        raise ValueError(f"docking report is incomplete or invalid: {panel_dir.name}")

    metrics_report = load_object(metrics_report_path, "metric report")
    if (
        metrics_report.get("contract") != contract["contract"]
        or metrics_report.get("status") != "complete"
        or metrics_report.get("attempts") != attempts
        or metrics_report.get("inputs", {}).get("docking_records_sha256")
        != sha256_file(docking_records)
        or metrics_report.get("output_records_sha256") != sha256_file(endpoint_records)
    ):
        raise ValueError(f"metric report is incomplete or invalid: {panel_dir.name}")

    qualifying_report = load_object(qualifying_report_path, "qualifying-hit report")
    if (
        qualifying_report.get("contract") != "q07820-qualifying-hit-v1"
        or qualifying_report.get("status") != "complete"
        or qualifying_report.get("attempts") != attempts
        or qualifying_report.get("infrastructure_failures") != 0
        or qualifying_report.get("inputs", {}).get("records_sha256")
        != sha256_file(endpoint_records)
        or qualifying_report.get("inputs", {}).get("thresholds_sha256") != thresholds_sha256
        or len(qualifying_report.get("scored_records", [])) != attempts
    ):
        raise ValueError(f"qualifying-hit report is incomplete or invalid: {panel_dir.name}")

    return {
        "arm": arm,
        "training_seed": seed,
        "checkpoint_step": step,
        "evaluation_seed": evaluation_seed,
        "policy_sha256": sample_manifest["identity"]["policy_sha256"],
        "sample_manifest_sha256": sha256_file(sample_manifest_path),
        "docking_report_sha256": sha256_file(docking_report_path),
        "metrics_report_sha256": sha256_file(metrics_report_path),
        "qualifying_report_sha256": sha256_file(qualifying_report_path),
    }


def gate_evaluation_matrix(
    contract_path: Path,
    thresholds_path: Path,
    panels_root: Path,
    panel_kind: str = "development",
) -> dict[str, Any]:
    contract = load_object(contract_path, "matched contract")
    contract_sha256 = sha256_file(contract_path)
    thresholds_sha256 = sha256_file(thresholds_path)
    expected = expected_panels(contract, panel_kind)
    expected_names = {panel_name(*panel) for panel in expected}
    observed_names = {path.name for path in panels_root.iterdir() if path.is_dir()}
    if observed_names != expected_names:
        missing = sorted(expected_names - observed_names)
        extra = sorted(observed_names - expected_names)
        raise ValueError(f"endpoint panel inventory differs: missing={missing}, extra={extra}")
    records = [
        verify_panel(
            panels_root / panel_name(arm, seed, step),
            contract,
            contract_sha256,
            thresholds_sha256,
            arm,
            seed,
            step,
        )
        for arm, seed, step in expected
    ]
    return {
        "schema_version": "anarres.molecular-endpoint-matrix-gate.v1",
        "study": contract["study"],
        "contract": contract["contract"],
        "panel_kind": panel_kind,
        "status": "ENDPOINT_MATRIX_COMPLETE__COMPARATIVE_SCORING_AUTHORIZED",
        "comparative_scoring_authorized": True,
        "contract_sha256": contract_sha256,
        "thresholds_sha256": thresholds_sha256,
        "panel_count": len(records),
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    parser.add_argument("--panels-root", type=Path, required=True)
    parser.add_argument(
        "--panel-kind", choices=("development", "prospective"), default="development"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.contract.resolve() != DEFAULT_CONTRACT.resolve():
        raise ValueError("claim-bearing gates require the released matched contract")
    if args.thresholds.resolve() != DEFAULT_THRESHOLDS.resolve():
        raise ValueError("claim-bearing gates require the released endpoint thresholds")
    if args.output.exists():
        raise FileExistsError(args.output)
    result = gate_evaluation_matrix(
        args.contract, args.thresholds, args.panels_root, args.panel_kind
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "panel_count": result["panel_count"]}, indent=2))


if __name__ == "__main__":
    main()
