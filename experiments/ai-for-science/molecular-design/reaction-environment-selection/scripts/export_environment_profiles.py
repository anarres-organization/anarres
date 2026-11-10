#!/usr/bin/env python3
"""Export qualified molecular replay banks as domain-preserving profiles."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from anarres.environments import (
    build_profile_input,
    coordinate,
    local_artifact,
    qualification_check,
    write_profile_input,
)

STUDY = Path(__file__).resolve().parents[1]
DEFAULT_RESULT = STUDY / "DEVELOPMENT_BANK_QUALIFICATION_V4.json"
DEFAULT_PRESERVED_RESULT = STUDY / "DEVELOPMENT_BANK_QUALIFICATION_V3.json"
DEFAULT_MEASUREMENT_RESULT = STUDY / "MEASUREMENT_RELIABILITY_RESULT_V3.json"
DEFAULT_MEASUREMENT_CONTRACT = STUDY / "MEASUREMENT_CONTRACT_V4.json"
DEFAULT_BANK_CONTRACT = STUDY / "BANK_CONSTRUCTION_CONTRACT_V4.json"
DEFAULT_WARM_START = STUDY / "WARM_START_QUALIFICATION.json"
DEFAULT_TARGET_SELECTION = STUDY / "TARGET_SELECTION_RESULT.json"
DEFAULT_SOURCE_AUDIT = STUDY / "SOURCE_AUDIT.json"
DEFAULT_ARCHIVE_AUDIT = STUDY / "MOLGENBENCH_ARCHIVE_AUDIT.json"
DEFAULT_FIXTURE_AUDIT = STUDY / "TARGET_FIXTURE_AUDIT.json"
DEFAULT_ORACLE_QUALIFICATION = STUDY / "ORACLE_QUALIFICATION.json"
DEFAULT_TARGET_REWARD = STUDY / "TARGET_REWARD_CONTRACT_V3.json"
DEFAULT_SUPERSEDED_AUDIT = STUDY / "DEVELOPMENT_BANK_QUALIFICATION_AUDIT_V1.json"
DEFAULT_SCORING_AUDIT = STUDY / "BANK_CONFIRMATION_SCORING_AUDIT_V2.json"
DEFAULT_PROTOCOL = STUDY / "PROTOCOL.json"
CONVENTION_URI = (
    "https://github.com/anarres-organization/anarres/blob/main/"
    "docs/conventions/molecular-reaction-bank-v1.md"
)
ADAPTER_ID = "molecular-design.rxnflow-reaction-bank"
ADAPTER_REVISION = "v2"
BANK_NAMES = (
    "hash_uniform",
    "reward_signal",
    "validity_cost",
    "scaffold_coverage",
    "route_coverage",
    "graph_embedding_coverage",
)
COORDINATES = {
    "mean_target_reward": (
        "target_affinity",
        "docking_qed_reward",
        "contextual",
        "arithmetic mean of frozen Q07820 terminal reward over bank members",
    ),
    "mean_generated_action_count": (
        "cost",
        "generated_molecular_actions_per_trajectory",
        "lower",
        "arithmetic mean generated molecular-action count over bank members",
    ),
    "mean_oracle_seconds": (
        "cost",
        "seconds_per_molecule",
        "lower",
        "arithmetic mean selected-target oracle wall time over bank members",
    ),
    "unique_scaffold_fraction": (
        "coverage",
        "fraction",
        "contextual",
        "distinct achiral Bemis-Murcko scaffolds divided by bank size",
    ),
    "unique_ring_systems_per_record": (
        "coverage",
        "ring_systems_per_record",
        "contextual",
        "distinct connected ring-system signatures divided by bank size",
    ),
    "unique_route_fraction": (
        "coverage",
        "fraction",
        "contextual",
        "distinct ordered reaction-name sequences divided by bank size",
    ),
    "unique_reaction_families": (
        "coverage",
        "reaction_families",
        "contextual",
        "count of distinct reaction families represented by bank members",
    ),
    "embedding_mean_nearest_neighbor_distance": (
        "coverage",
        "normalized_embedding_distance",
        "contextual",
        "mean within-bank nearest-neighbor distance in frozen normalized representation",
    ),
}


class AdapterError(ValueError):
    """Raised when native molecular evidence cannot support exact profiles."""


def read_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AdapterError(f"required native artifact does not exist: {path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AdapterError(f"expected an object in {path.name}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_finite_nonnegative(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AdapterError(f"{name} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise AdapterError(f"{name} must be finite and nonnegative")
    return number


def require_finite_correlation(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AdapterError(f"{name} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < -1 or number > 1:
        raise AdapterError(f"{name} must be finite and lie in [-1, 1]")
    return number


def validate_inputs(
    result: dict[str, Any],
    preserved_result: dict[str, Any],
    measurement_result: dict[str, Any],
    measurement_contract: dict[str, Any],
    bank_contract: dict[str, Any],
    warm_start: dict[str, Any],
    target_selection: dict[str, Any],
    source_audit: dict[str, Any],
    archive_audit: dict[str, Any],
    fixture_audit: dict[str, Any],
    oracle_qualification: dict[str, Any],
    target_reward: dict[str, Any],
    superseded_audit: dict[str, Any],
    scoring_audit: dict[str, Any],
    protocol: dict[str, Any],
) -> None:
    if result.get("schema_version") != "4.0" or result.get("qualification") not in {
        "pass",
        "fail",
    }:
        raise AdapterError("bank result is not a scored version 4 qualification")
    if result.get("study") != "prospective-reaction-environment-selection":
        raise AdapterError("bank result belongs to a different study")
    if bank_contract.get("schema_version") != "4.0":
        raise AdapterError("bank result requires the version 4 bank contract")
    rule = bank_contract.get("confirmation_rule", {})
    if rule.get("kind") != "selector_fidelity":
        raise AdapterError("version 4 bank result requires the selector-fidelity gate")
    expected_seeds = [rule.get("construction_view_seed"), rule.get("confirmation_view_seed")]
    if result.get("view_seeds") != expected_seeds:
        raise AdapterError("bank result view seeds do not match the bank contract")
    if measurement_contract.get("schema_version") != "4.0":
        raise AdapterError("bank result requires the version 4 measurement contract")
    if expected_seeds[0] != measurement_contract.get("sampling", {}).get("construction_view_seed"):
        raise AdapterError("construction seed differs between measurement and bank contracts")
    if measurement_result.get("qualification") != "pass":
        raise AdapterError("starting-policy measurement reliability did not pass")
    if any(not all(checks.values()) for checks in measurement_result["per_view_checks"]):
        raise AdapterError("measurement record contains a failed per-view check")
    if not all(measurement_result["two_view_checks"].values()):
        raise AdapterError("measurement record contains a failed two-view check")
    if any(view.get("oracle_completion_fraction") != 1.0 for view in measurement_result["views"]):
        raise AdapterError("measurement record contains an infrastructure-invalid oracle result")
    if warm_start.get("qualification") != "pass":
        raise AdapterError("starting policy did not pass qualification")
    policy = warm_start.get("artifacts", {}).get("weights_only_starting_policy", {})
    if not re.fullmatch(r"[0-9a-f]{64}", str(policy.get("sha256", ""))):
        raise AdapterError("starting-policy artifact revision is absent or invalid")
    if target_selection.get("decision") != "select" or target_selection.get(
        "selected_target"
    ) != target_reward.get("selected_target"):
        raise AdapterError("target identity is missing or inconsistent")
    if source_audit.get("rxnflow", {}).get("qualification") != "pass":
        raise AdapterError("RxnFlow source qualification did not pass")
    if not re.fullmatch(r"[0-9a-f]{40}", source_audit["rxnflow"].get("commit", "")):
        raise AdapterError("RxnFlow source revision is absent or invalid")
    if archive_audit.get("qualification") != "archive_metadata_pass_target_contents_open":
        raise AdapterError("MolGenBench archive qualification did not pass")
    archive_sha256 = archive_audit.get("archive", {}).get("sha256")
    if not re.fullmatch(r"[0-9a-f]{64}", str(archive_sha256 or "")):
        raise AdapterError("MolGenBench archive revision is absent or invalid")
    if fixture_audit.get("archive_sha256") != archive_sha256:
        raise AdapterError("target fixtures are not bound to the audited archive")
    if fixture_audit.get("qualification") != "target_fixture_structure_pass_oracle_behavior_open":
        raise AdapterError("target-fixture structure qualification did not pass")
    selected_target = target_selection.get("selected_target")
    fixture = next(
        (
            item
            for item in fixture_audit.get("targets", [])
            if item.get("target_id") == selected_target
        ),
        None,
    )
    if fixture is None or fixture.get("fixture_integrity") != "pass":
        raise AdapterError("selected target is absent from the qualified fixture panel")
    if oracle_qualification.get("qualification") != "pass":
        raise AdapterError("docking-oracle qualification did not pass")
    oracle_target = next(
        (
            item
            for item in oracle_qualification.get("targets", [])
            if item.get("target_id") == selected_target
        ),
        None,
    )
    if oracle_target is None or oracle_target.get("qualification") != "pass":
        raise AdapterError("selected target is absent from the qualified oracle panel")
    oracle_sealed = oracle_qualification.get("sealed_boundary", {})
    if oracle_sealed.get("training_or_evaluation_outcomes_opened") is not False:
        raise AdapterError("oracle qualification opened downstream outcomes")
    if target_reward.get("schema_version") != "3.0":
        raise AdapterError("target reward contract is not version 3")
    if superseded_audit.get("audit_status") != "non_authorizing_seed_binding_mismatch":
        raise AdapterError("superseded bank-result status is not preserved")
    if scoring_audit.get("audit_status") != "non_authorizing_unsupported_ligand_atom_type":
        raise AdapterError("superseded scoring-failure status is not preserved")
    if (
        preserved_result.get("schema_version") != "3.0"
        or preserved_result.get("qualification") != "fail"
    ):
        raise AdapterError("failed version 3 bank result is not preserved")
    if scoring_audit.get("input_sha256") not in preserved_result.get("source_sha256", {}).values():
        raise AdapterError("superseded scoring audit is not bound to the preserved version 3 view")
    sealed = protocol.get("sealed_boundary", {})
    if sealed.get("training_or_evaluation_outcomes_inspected") is not False:
        raise AdapterError("target-training outcomes are not sealed")
    if sealed.get("development_training_started") is not False:
        raise AdapterError("development training has already started")
    if result.get("bank_size") != bank_contract.get("bank_size"):
        raise AdapterError("bank size differs from the frozen contract")
    if len(result.get("eligible_unique_products", [])) != 2 or any(
        int(count) < int(result["bank_size"]) for count in result["eligible_unique_products"]
    ):
        raise AdapterError("eligible unique-product support is incomplete")
    if set(result.get("construction_memberships", {})) != set(BANK_NAMES):
        raise AdapterError("bank result does not contain the exact frozen candidate order")
    if set(result.get("confirmation_reconstruction_memberships", {})) != set(BANK_NAMES):
        raise AdapterError("bank confirmation memberships are incomplete")
    if set(result.get("summaries", [{}])[0]) != set(BANK_NAMES):
        raise AdapterError("bank summaries do not contain the exact frozen candidate order")
    checks = result.get("confirmation_checks", {})
    expected_checks = {check["check_id"] for check in rule.get("checks", [])}
    if (
        len(expected_checks) != len(rule.get("checks", []))
        or set(checks) != expected_checks
        or any(not isinstance(value, bool) for value in checks.values())
    ):
        raise AdapterError("bank confirmation checks are incomplete or invalid")
    input_digests = result.get("input_sha256", {})
    if len(input_digests) != 4 or any(
        not re.fullmatch(r"[0-9a-f]{64}", str(digest)) for digest in input_digests.values()
    ):
        raise AdapterError("bank result input digests are absent or invalid")
    for name in COORDINATES:
        correlation = result.get("rank_correlations", {}).get(name, {}).get("spearman")
        require_finite_correlation(f"rank correlation {name}", correlation)
    view_checks = result.get("selector_fidelity_checks_by_view", [])
    if len(view_checks) != 2 or any(set(view) != expected_checks for view in view_checks):
        raise AdapterError("per-view selector-fidelity checks are incomplete")
    if any(not isinstance(value, bool) for view in view_checks for value in view.values()):
        raise AdapterError("per-view selector-fidelity checks are invalid")
    for check_id in expected_checks:
        if checks[check_id] is not all(view[check_id] for view in view_checks):
            raise AdapterError(f"combined selector-fidelity status is inconsistent: {check_id}")
    if (result["qualification"] == "pass") is not all(checks.values()):
        raise AdapterError("aggregate bank qualification is inconsistent with coordinate checks")
    size = int(result["bank_size"])
    for bank in BANK_NAMES:
        members = result["construction_memberships"][bank]
        if len(members) != size or len(set(members)) != size:
            raise AdapterError(f"{bank} membership is incomplete or duplicated")
        if any(not re.fullmatch(r"[0-9a-f]{64}", str(member)) for member in members):
            raise AdapterError(f"{bank} contains an invalid record identity")
        confirmation_members = result["confirmation_reconstruction_memberships"][bank]
        if len(confirmation_members) != size or len(set(confirmation_members)) != size:
            raise AdapterError(f"{bank} confirmation membership is incomplete or duplicated")
        summary = result["summaries"][0][bank]
        if set(summary) != set(COORDINATES):
            raise AdapterError(f"{bank} summary coordinates are incomplete")
        for name, value in summary.items():
            require_finite_nonnegative(f"{bank}.{name}", value)


def export_profiles(
    *,
    result_path: Path = DEFAULT_RESULT,
    preserved_result_path: Path = DEFAULT_PRESERVED_RESULT,
    measurement_result_path: Path = DEFAULT_MEASUREMENT_RESULT,
    measurement_contract_path: Path = DEFAULT_MEASUREMENT_CONTRACT,
    bank_contract_path: Path = DEFAULT_BANK_CONTRACT,
    warm_start_path: Path = DEFAULT_WARM_START,
    target_selection_path: Path = DEFAULT_TARGET_SELECTION,
    source_audit_path: Path = DEFAULT_SOURCE_AUDIT,
    archive_audit_path: Path = DEFAULT_ARCHIVE_AUDIT,
    fixture_audit_path: Path = DEFAULT_FIXTURE_AUDIT,
    oracle_qualification_path: Path = DEFAULT_ORACLE_QUALIFICATION,
    target_reward_path: Path = DEFAULT_TARGET_REWARD,
    superseded_audit_path: Path = DEFAULT_SUPERSEDED_AUDIT,
    scoring_audit_path: Path = DEFAULT_SCORING_AUDIT,
    protocol_path: Path = DEFAULT_PROTOCOL,
    output_dir: Path,
    force: bool = False,
) -> list[Path]:
    """Export one profile per qualified molecular development bank."""

    paths = {
        "bank-qualification": result_path,
        "preserved-bank-qualification": preserved_result_path,
        "measurement-qualification": measurement_result_path,
        "measurement-contract": measurement_contract_path,
        "bank-contract": bank_contract_path,
        "starting-policy-qualification": warm_start_path,
        "target-selection": target_selection_path,
        "source-audit": source_audit_path,
        "source-archive-audit": archive_audit_path,
        "target-fixture-audit": fixture_audit_path,
        "oracle-qualification": oracle_qualification_path,
        "target-reward-contract": target_reward_path,
        "superseded-qualification-audit": superseded_audit_path,
        "superseded-scoring-audit": scoring_audit_path,
        "study-protocol": protocol_path,
    }
    values = {role: read_object(path) for role, path in paths.items()}
    validate_inputs(
        values["bank-qualification"],
        values["preserved-bank-qualification"],
        values["measurement-qualification"],
        values["measurement-contract"],
        values["bank-contract"],
        values["starting-policy-qualification"],
        values["target-selection"],
        values["source-audit"],
        values["source-archive-audit"],
        values["target-fixture-audit"],
        values["oracle-qualification"],
        values["target-reward-contract"],
        values["superseded-qualification-audit"],
        values["superseded-scoring-audit"],
        values["study-protocol"],
    )
    result = values["bank-qualification"]
    bank_contract = values["bank-contract"]
    policy = values["starting-policy-qualification"]["artifacts"]["weights_only_starting_policy"]
    target_id = values["target-selection"]["selected_target"]
    source_audit = values["source-audit"]
    source_revision = sha256(result_path)
    bank_confirmation_passed = result["qualification"] == "pass"
    failed_checks = sorted(
        name for name, passed in result["confirmation_checks"].items() if not passed
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [output_dir / f"{target_id.lower()}-{bank}.profile-input.json" for bank in BANK_NAMES]
    if not force:
        existing = [path for path in outputs if path.exists()]
        if existing:
            raise FileExistsError(existing[0])
    profiles = []
    for bank in BANK_NAMES:
        measured = result["summaries"][0][bank]
        coordinates = []
        for name, (role, unit, direction, estimator) in COORDINATES.items():
            coordinates.append(
                coordinate(
                    name=name,
                    definition_uri=CONVENTION_URI,
                    definition_revision="v1-development",
                    role=role,
                    value=float(measured[name]),
                    unit=unit,
                    direction=direction,
                    estimator=estimator,
                    sample_count=int(result["bank_size"]),
                )
            )
        profile = build_profile_input(
            environment_id=f"{target_id.lower()}-{bank}-v4",
            domain="molecular-design",
            subject={
                "kind": "molecular-graph-policy",
                "id": "RxnFlow-v2.1.0-QED-warm-start",
                "revision": f"sha256:{policy['sha256']}",
            },
            producer={
                "kind": "domain-adapter",
                "id": ADAPTER_ID,
                "revision": ADAPTER_REVISION,
            },
            source={
                "uri": (
                    "repo://experiments/ai-for-science/molecular-design/"
                    "reaction-environment-selection/DEVELOPMENT_BANK_QUALIFICATION_V4.json"
                ),
                "revision": f"sha256:{source_revision}",
                "license": "Apache-2.0",
            },
            measurement_contract={
                "kind": "molecular-reaction-bank-probe",
                "id": "rxnflow-q07820-bank-v4",
                "revision": "v4",
                "repetitions": 2,
                "cost_unit": "generated_molecular_actions",
            },
            qualification_checks=[
                qualification_check(
                    check_id="source-qualified",
                    category="source",
                    status="pass",
                    severity="error",
                    summary="Pinned RxnFlow and MolGenBench sources passed the native audit.",
                ),
                qualification_check(
                    check_id="starting-policy-qualified",
                    category="measurement",
                    status="pass",
                    severity="error",
                    summary="The common weights-only QED warm start passed qualification.",
                ),
                qualification_check(
                    check_id="target-qualified",
                    category="verifier",
                    status="pass",
                    severity="error",
                    summary="Q07820 passed the frozen target and oracle selection gates.",
                ),
                qualification_check(
                    check_id="oracle-infrastructure-valid",
                    category="infrastructure",
                    status="pass",
                    severity="error",
                    summary=(
                        "Every selected-target measurement completed without "
                        "infrastructure failure."
                    ),
                ),
                qualification_check(
                    check_id="measurement-reliability",
                    category="measurement",
                    status="pass",
                    severity="error",
                    summary="Both version 3 views passed every support and stability gate.",
                ),
                qualification_check(
                    check_id="bank-confirmation",
                    category="measurement",
                    status="pass" if bank_confirmation_passed else "fail",
                    severity="error",
                    summary=(
                        "All eight selector-fidelity checks passed in both independent views."
                        if bank_confirmation_passed
                        else "Independent-view selector fidelity failed for: "
                        + ", ".join(failed_checks)
                        + "."
                    ),
                ),
                qualification_check(
                    check_id="training-outcomes-sealed",
                    category="source",
                    status="pass",
                    severity="error",
                    summary=(
                        "No target-training or evaluation outcome entered candidate measurement."
                    ),
                ),
            ],
            coordinates=coordinates,
            artifacts=[
                local_artifact(
                    role=role,
                    path=path,
                    uri=f"repo://experiments/ai-for-science/molecular-design/reaction-environment-selection/{path.name}",
                    media_type="application/json",
                    license_id="Apache-2.0",
                    producing_run=(
                        "prospective-reaction-environment-selection"
                        if role in {"bank-qualification", "measurement-qualification"}
                        else None
                    ),
                )
                for role, path in paths.items()
            ],
            attributes={
                "target_id": target_id,
                "rxnflow_revision": source_audit["rxnflow"]["commit"],
                "molgenbench_revision": source_audit["molgenbench"]["commit"],
                "bank_name": bank,
                "bank_size": int(result["bank_size"]),
                "construction_view_seed": int(
                    bank_contract["confirmation_rule"]["construction_view_seed"]
                ),
                "confirmation_view_seed": int(
                    bank_contract["confirmation_rule"]["confirmation_view_seed"]
                ),
                "training_outcomes_opened": False,
                "predictive_evidence_available": False,
                "target_reward_contract_revision": "v3",
                "bank_confirmation_passed": bank_confirmation_passed,
                "confirmation_rule": "selector_fidelity",
                "failed_confirmation_checks": ",".join(failed_checks),
            },
        )
        profiles.append(profile)
    for output, profile in zip(outputs, profiles, strict=True):
        write_profile_input(output, profile, force=force)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--preserved-result", type=Path, default=DEFAULT_PRESERVED_RESULT)
    parser.add_argument("--measurement-result", type=Path, default=DEFAULT_MEASUREMENT_RESULT)
    parser.add_argument("--measurement-contract", type=Path, default=DEFAULT_MEASUREMENT_CONTRACT)
    parser.add_argument("--bank-contract", type=Path, default=DEFAULT_BANK_CONTRACT)
    parser.add_argument("--warm-start", type=Path, default=DEFAULT_WARM_START)
    parser.add_argument("--target-selection", type=Path, default=DEFAULT_TARGET_SELECTION)
    parser.add_argument("--source-audit", type=Path, default=DEFAULT_SOURCE_AUDIT)
    parser.add_argument("--archive-audit", type=Path, default=DEFAULT_ARCHIVE_AUDIT)
    parser.add_argument("--fixture-audit", type=Path, default=DEFAULT_FIXTURE_AUDIT)
    parser.add_argument("--oracle-qualification", type=Path, default=DEFAULT_ORACLE_QUALIFICATION)
    parser.add_argument("--target-reward", type=Path, default=DEFAULT_TARGET_REWARD)
    parser.add_argument("--superseded-audit", type=Path, default=DEFAULT_SUPERSEDED_AUDIT)
    parser.add_argument("--scoring-audit", type=Path, default=DEFAULT_SCORING_AUDIT)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    outputs = export_profiles(
        result_path=args.result,
        preserved_result_path=args.preserved_result,
        measurement_result_path=args.measurement_result,
        measurement_contract_path=args.measurement_contract,
        bank_contract_path=args.bank_contract,
        warm_start_path=args.warm_start,
        target_selection_path=args.target_selection,
        source_audit_path=args.source_audit,
        archive_audit_path=args.archive_audit,
        fixture_audit_path=args.fixture_audit,
        oracle_qualification_path=args.oracle_qualification,
        target_reward_path=args.target_reward,
        superseded_audit_path=args.superseded_audit,
        scoring_audit_path=args.scoring_audit,
        protocol_path=args.protocol,
        output_dir=args.output_dir,
        force=args.force,
    )
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
