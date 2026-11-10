#!/usr/bin/env python3
"""Export released MLIP candidate measurements as Anarres profiles."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from anarres.environments import (
    build_profile_input,
    coordinate,
    local_artifact,
    qualification_check,
    write_profile_input,
)

STUDY = Path(__file__).resolve().parent
DEFAULT_BANK = STUDY / "FINAL_COST_MATCHED_PANEL.json"
DEFAULT_VALIDATION = STUDY / "FULL_MEASUREMENT_VALIDATION.json"
DEFAULT_SOURCE = STUDY / "SOURCE_QUALIFICATION.json"
DEFAULT_CHECKPOINT = STUDY / "CHECKPOINT_QUALIFICATION.json"
DEFAULT_OVERLAP = STUDY / "OMAT24_TARGET_OVERLAP_AUDIT.json"
DEFAULT_TARGET_ROLES = STUDY / "TARGET_ROLES.json"
DEFAULT_POOL = STUDY / "MEASUREMENT_POOL_SUMMARY.json"
CONVENTION_URI = (
    "https://github.com/anarres-organization/anarres/blob/main/"
    "docs/conventions/materials-mlip-candidate-measurement-v2.md"
)
ADAPTER_ID = "materials.mlip-phonon-candidate-measurement"
ADAPTER_REVISION = "v2"
MODEL_SHA256 = "1647af8e627e1afa11e2bfadeab0797326513a521afd7dd01606a96f56783eee"
OMAT24_SHA256 = "789ecc1306575a1652806b339265d7659c57282eeb1b3e3b54ba0e1154938b81"
EXPECTED_DIGESTS = {
    "FINAL_COST_MATCHED_PANEL.json": (
        "b5d26ea2dbecac0e530e80d470b6079a7ebee46600633f119eb6d94b9048dd52"
    ),
    "FULL_MEASUREMENT_VALIDATION.json": (
        "a119444de6a8dbe57866d5a7c052f75221c07d97183feff78ce6a15f648d755c"
    ),
    "SOURCE_QUALIFICATION.json": (
        "a807e0ab1bc729886b49061d7fccac0a2766a0fb985a8619528ed83e7ffb9c72"
    ),
    "CHECKPOINT_QUALIFICATION.json": (
        "89864d82053718f4f6dc53ee9f852f574727f805f493b47eae23a2b797253fc2"
    ),
    "OMAT24_TARGET_OVERLAP_AUDIT.json": (
        "8f777b5cb4eca3233130a19ecc853c64445527457e85c4a28b2e9b1ec75da952"
    ),
    "TARGET_ROLES.json": ("3af598f1cf652e4918f37a2359242b29d89ed3fea40f12125cbbdc66ab73169f"),
    "MEASUREMENT_POOL_SUMMARY.json": (
        "0a41d3d5f0ce02f87f23a34a093245463f600e0fdc65705e4942b98cf498ef7b"
    ),
}


class AdapterError(ValueError):
    """Raised when released materials evidence cannot support a profile."""


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise AdapterError(f"required native artifact is missing: {path}") from error
    if not isinstance(value, dict):
        raise AdapterError(f"expected a JSON object in {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except FileNotFoundError as error:
        raise AdapterError(f"required native artifact is missing: {path}") from error
    return digest.hexdigest()


def require_digest(path: Path) -> None:
    expected = EXPECTED_DIGESTS.get(path.name)
    if expected is None:
        raise AdapterError(f"no pinned digest is defined for {path.name}")
    observed = sha256(path)
    if observed != expected:
        raise AdapterError(f"{path.name} digest differs from the adapter revision: {observed}")


def finite_number(candidate: dict[str, Any], field: str) -> float:
    value = candidate.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AdapterError(f"{candidate.get('candidate_id')} is missing numeric {field}")
    number = float(value)
    if not math.isfinite(number):
        raise AdapterError(f"{candidate.get('candidate_id')} has nonfinite {field}")
    return number


def validate_inputs(
    *,
    paths: list[Path],
    target_roles_path: Path,
    bank: dict[str, Any],
    validation: dict[str, Any],
    source: dict[str, Any],
    checkpoint: dict[str, Any],
    overlap: dict[str, Any],
    target_roles: dict[str, Any],
    pool: dict[str, Any],
) -> None:
    for path in paths:
        require_digest(path)

    if bank.get("artifact") != "anarres_mlip_cost_matched_panel_v1":
        raise AdapterError("unsupported MLIP final-panel artifact")
    if bank.get("status") != "frozen_pretraining__candidate_outcomes_sealed":
        raise AdapterError("candidate panel is not frozen with outcomes sealed")
    construction = bank.get("construction", {})
    if construction.get("uses_candidate_training_outcomes") is not False:
        raise AdapterError("candidate construction used candidate training outcomes")
    if construction.get("uses_development_or_prospective_target_outcomes") is not False:
        raise AdapterError("candidate construction used protected target outcomes")
    if construction.get("atom_budget_per_candidate") != 50_000:
        raise AdapterError("candidate panel does not use the frozen 50,000-atom budget")
    if construction.get("neighbor_edge_budget_per_candidate") != 2_100_000:
        raise AdapterError("candidate panel does not use the frozen graph-edge budget")
    if construction.get("maximum_records_per_parent") != 1:
        raise AdapterError("candidate panel does not preserve the one-record parent cap")

    if source.get("status") != "qualified":
        raise AdapterError("OMat24 and Alexandria sources are not qualified")
    archive = source.get("construction_reservoir", {}).get("archive", {})
    if archive.get("sha256") != OMAT24_SHA256:
        raise AdapterError("OMat24 source revision differs from the adapter contract")
    if source.get("construction_reservoir", {}).get("license") != "CC BY 4.0":
        raise AdapterError("OMat24 source license is missing or changed")

    if checkpoint.get("status") != "complete" or checkpoint.get("selected_backend") != "nequix":
        raise AdapterError("Nequix-MP-1 is not the qualified starting checkpoint")
    selected_hashes = checkpoint.get("checkpoints", {}).get("nequix", {}).get("model_sha256")
    if selected_hashes != [MODEL_SHA256]:
        raise AdapterError("starting-model hash differs from the adapter contract")

    if target_roles.get("status") != "frozen":
        raise AdapterError("target roles are not frozen")
    target_digest = sha256(target_roles_path)
    if bank.get("inputs", {}).get("target_roles_sha256") != target_digest:
        raise AdapterError("candidate panel does not match the frozen target roles")
    if checkpoint.get("panel", {}).get("role_manifest_sha256") != target_digest:
        raise AdapterError("checkpoint qualification does not match the target roles")
    if overlap.get("status") != "complete":
        raise AdapterError("target-overlap audit is incomplete")
    if overlap.get("inputs", {}).get("roles_sha256") != target_digest:
        raise AdapterError("overlap audit does not match the target roles")

    if validation.get("status") != "complete" or validation.get("records") != 80_000:
        raise AdapterError("full starting-model measurement is incomplete")
    if validation.get("model_sha256") != MODEL_SHA256:
        raise AdapterError("measurement validation uses a different starting model")
    manifest_digest = validation.get("manifest_sha256")
    if bank.get("inputs", {}).get("manifest_sha256") != manifest_digest:
        raise AdapterError("candidate panel does not match the validated measurement manifest")
    if pool.get("status") != "complete":
        raise AdapterError("measurement-pool construction is incomplete")
    if pool.get("pool", {}).get("manifest_sha256") != manifest_digest:
        raise AdapterError("measurement-pool summary uses a different manifest")
    if bank.get("inputs", {}).get("measurement_sha256") != validation.get("measurement_sha256"):
        raise AdapterError("candidate panel does not match the validated measurement shards")

    candidates = bank.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 16:
        raise AdapterError("released final panel must contain exactly 16 candidates")
    candidate_ids = [candidate.get("candidate_id") for candidate in candidates]
    if any(not isinstance(value, str) or not value for value in candidate_ids):
        raise AdapterError("candidate panel contains an invalid candidate identity")
    if len(set(candidate_ids)) != len(candidate_ids):
        raise AdapterError("candidate identities are not unique")
    roles = [candidate.get("role") for candidate in candidates]
    if roles.count("development") != 12 or roles.count("prospective") != 4:
        raise AdapterError(
            "final panel must contain 12 development and four prospective candidates"
        )
    for candidate in candidates:
        candidate_id = candidate["candidate_id"]
        records = candidate.get("records")
        indices = candidate.get("record_indices")
        if not isinstance(records, int) or records <= 0:
            raise AdapterError(f"{candidate_id} has an invalid record count")
        if not isinstance(indices, list) or len(indices) != records:
            raise AdapterError(f"{candidate_id} does not preserve every record identity")
        if len(set(indices)) != len(indices) or any(
            not isinstance(index, int) or index < 0 or index >= 80_000 for index in indices
        ):
            raise AdapterError(f"{candidate_id} has invalid or repeated record indices")
        if candidate.get("atoms") != 50_000:
            raise AdapterError(f"{candidate_id} is not matched to 50,000 atoms")
        if candidate.get("neighbor_edges") != 2_100_000:
            raise AdapterError(f"{candidate_id} is not matched to 2,100,000 neighbor edges")
        if candidate.get("parents") != records:
            raise AdapterError(f"{candidate_id} violates the one-record parent cap")
        membership = candidate.get("membership_sha256")
        if not isinstance(membership, str) or len(membership) != 64:
            raise AdapterError(f"{candidate_id} has an invalid membership digest")
        if candidate.get("role") not in {"development", "prospective"}:
            raise AdapterError(f"{candidate_id} has an invalid frozen role")
        for field in (
            "signal_density_per_atom",
            "effective_signal_coverage",
            "chemical_system_entropy",
            "mean_target_affinity",
            "neighbor_edges_per_atom",
        ):
            finite_number(candidate, field)
    panel_audit = bank.get("panel_audit", {})
    if panel_audit.get("candidate_count") != 16:
        raise AdapterError("final-panel audit does not preserve the candidate count")
    if panel_audit.get("role_counts") != {"development": 12, "prospective": 4}:
        raise AdapterError("final-panel audit does not preserve the frozen role counts")


def export_profiles(
    *,
    bank_path: Path = DEFAULT_BANK,
    validation_path: Path = DEFAULT_VALIDATION,
    source_path: Path = DEFAULT_SOURCE,
    checkpoint_path: Path = DEFAULT_CHECKPOINT,
    overlap_path: Path = DEFAULT_OVERLAP,
    target_roles_path: Path = DEFAULT_TARGET_ROLES,
    pool_path: Path = DEFAULT_POOL,
    output_dir: Path,
    candidate_ids: list[str] | None = None,
    force: bool = False,
) -> list[Path]:
    """Export compatible profiles from the released 16-candidate final panel."""

    paths = [
        bank_path,
        validation_path,
        source_path,
        checkpoint_path,
        overlap_path,
        target_roles_path,
        pool_path,
    ]
    bank = read_object(bank_path)
    validation = read_object(validation_path)
    source = read_object(source_path)
    checkpoint = read_object(checkpoint_path)
    overlap = read_object(overlap_path)
    target_roles = read_object(target_roles_path)
    pool = read_object(pool_path)
    validate_inputs(
        paths=paths,
        target_roles_path=target_roles_path,
        bank=bank,
        validation=validation,
        source=source,
        checkpoint=checkpoint,
        overlap=overlap,
        target_roles=target_roles,
        pool=pool,
    )

    by_id = {candidate["candidate_id"]: candidate for candidate in bank["candidates"]}
    selected_ids = sorted(candidate_ids or by_id)
    missing = sorted(set(selected_ids) - set(by_id))
    if missing:
        raise AdapterError(f"unknown candidate identity: {missing[0]}")
    if len(selected_ids) != len(set(selected_ids)):
        raise AdapterError("candidate identities were requested more than once")

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [output_dir / f"{candidate_id}.profile-input.json" for candidate_id in selected_ids]
    if not force:
        existing = [path for path in outputs if path.exists()]
        if existing:
            raise FileExistsError(existing[0])

    artifacts = [
        local_artifact(
            role="final-training-panel",
            path=bank_path,
            uri=(
                "repo://experiments/ai-for-science/materials-science/"
                "mlip-phonon-environment-selection/FINAL_COST_MATCHED_PANEL.json"
            ),
            media_type="application/json",
            license_id="CC-BY-4.0",
            producing_run=bank["artifact"],
        ),
        local_artifact(
            role="measurement-validation",
            path=validation_path,
            uri=(
                "repo://experiments/ai-for-science/materials-science/"
                "mlip-phonon-environment-selection/FULL_MEASUREMENT_VALIDATION.json"
            ),
            media_type="application/json",
            license_id="Apache-2.0",
        ),
        local_artifact(
            role="source-qualification",
            path=source_path,
            uri=(
                "repo://experiments/ai-for-science/materials-science/"
                "mlip-phonon-environment-selection/SOURCE_QUALIFICATION.json"
            ),
            media_type="application/json",
            license_id="Apache-2.0",
        ),
        local_artifact(
            role="checkpoint-qualification",
            path=checkpoint_path,
            uri=(
                "repo://experiments/ai-for-science/materials-science/"
                "mlip-phonon-environment-selection/CHECKPOINT_QUALIFICATION.json"
            ),
            media_type="application/json",
            license_id="Apache-2.0",
        ),
        local_artifact(
            role="target-overlap-audit",
            path=overlap_path,
            uri=(
                "repo://experiments/ai-for-science/materials-science/"
                "mlip-phonon-environment-selection/OMAT24_TARGET_OVERLAP_AUDIT.json"
            ),
            media_type="application/json",
            license_id="Apache-2.0",
        ),
        local_artifact(
            role="target-roles",
            path=target_roles_path,
            uri=(
                "repo://experiments/ai-for-science/materials-science/"
                "mlip-phonon-environment-selection/TARGET_ROLES.json"
            ),
            media_type="application/json",
            license_id="Apache-2.0",
        ),
        local_artifact(
            role="measurement-pool-summary",
            path=pool_path,
            uri=(
                "repo://experiments/ai-for-science/materials-science/"
                "mlip-phonon-environment-selection/MEASUREMENT_POOL_SUMMARY.json"
            ),
            media_type="application/json",
            license_id="Apache-2.0",
        ),
    ]

    profiles = []
    for candidate_id in selected_ids:
        candidate = by_id[candidate_id]
        source_family, selection_rule = candidate_id.rsplit("__", 1)
        records = candidate["records"]
        profile = build_profile_input(
            environment_id=candidate_id,
            domain="materials-interatomic-potentials",
            subject={
                "kind": "interatomic-potential",
                "id": "Nequix-MP-1",
                "revision": f"sha256:{MODEL_SHA256}",
            },
            producer={
                "kind": "domain-adapter",
                "id": ADAPTER_ID,
                "revision": ADAPTER_REVISION,
            },
            source={
                "uri": source["construction_reservoir"]["archive"]["url"],
                "revision": f"sha256:{OMAT24_SHA256}",
                "license": "CC-BY-4.0",
            },
            measurement_contract={
                "kind": "starting-model-atomistic-residual-audit",
                "id": "materials.mlip-phonon-candidate-measurement.v2",
                "revision": "v2",
                "repetitions": 1,
                "cost_unit": "processed_atoms",
            },
            qualification_checks=[
                qualification_check(
                    check_id="source-qualified",
                    category="source",
                    status="pass",
                    severity="error",
                    summary="The OMat24 source revision and license passed qualification.",
                ),
                qualification_check(
                    check_id="starting-model-qualified",
                    category="measurement",
                    status="pass",
                    severity="error",
                    summary="The candidate was measured with the qualified Nequix-MP-1 checkpoint.",
                ),
                qualification_check(
                    check_id="target-roles-frozen",
                    category="source",
                    status="pass",
                    severity="error",
                    summary="Qualification, development, and prospective target roles are frozen.",
                ),
                qualification_check(
                    check_id="target-overlap-audited",
                    category="source",
                    status="pass",
                    severity="error",
                    summary=(
                        "Candidate construction applies the frozen composition-level exclusion."
                    ),
                ),
                qualification_check(
                    check_id="measurements-complete",
                    category="measurement",
                    status="pass",
                    severity="error",
                    summary="All 80,000 starting-model measurements passed the integrity audit.",
                ),
                qualification_check(
                    check_id="candidate-outcomes-sealed",
                    category="measurement",
                    status="pass",
                    severity="error",
                    summary="Candidate training and protected phonon outcomes were not used.",
                ),
                qualification_check(
                    check_id="candidate-membership-valid",
                    category="measurement",
                    status="pass",
                    severity="error",
                    summary="The candidate has 50,000 atoms and one record per parent.",
                ),
                qualification_check(
                    check_id="final-panel-frozen",
                    category="measurement",
                    status="pass",
                    severity="error",
                    summary="The final panel matches atom and neighbor-edge budgets exactly.",
                ),
            ],
            coordinates=[
                coordinate(
                    name="signal_density_per_atom",
                    definition_uri=f"{CONVENTION_URI}#signal_density_per_atom",
                    definition_revision="v2-frozen",
                    role="signal",
                    value=finite_number(candidate, "signal_density_per_atom"),
                    unit="loss_weighted_residual_per_atom",
                    direction="contextual",
                    estimator="atom-normalized sum of loss-weighted force and stress residual mass",
                    sample_count=records,
                ),
                coordinate(
                    name="effective_signal_coverage",
                    definition_uri=f"{CONVENTION_URI}#effective_signal_coverage",
                    definition_revision="v2-frozen",
                    role="coverage",
                    value=finite_number(candidate, "effective_signal_coverage"),
                    unit="fraction",
                    direction="contextual",
                    estimator="normalized effective sample size over structure signal masses",
                    sample_count=records,
                ),
                coordinate(
                    name="chemical_system_entropy",
                    definition_uri=f"{CONVENTION_URI}#chemical_system_entropy",
                    definition_revision="v2-frozen",
                    role="coverage",
                    value=finite_number(candidate, "chemical_system_entropy"),
                    unit="fraction",
                    direction="contextual",
                    estimator="normalized Shannon entropy over structure chemical-system labels",
                    sample_count=records,
                ),
                coordinate(
                    name="mean_target_affinity",
                    definition_uri=f"{CONVENTION_URI}#mean_target_affinity",
                    definition_revision="v2-frozen",
                    role="target_affinity",
                    value=finite_number(candidate, "mean_target_affinity"),
                    unit="fraction",
                    direction="contextual",
                    estimator="arithmetic mean of maximum element-set Jaccard similarity",
                    sample_count=records,
                ),
                coordinate(
                    name="neighbor_edges_per_atom",
                    definition_uri=f"{CONVENTION_URI}#neighbor_edges_per_atom",
                    definition_revision="v2-frozen",
                    role="cost",
                    value=finite_number(candidate, "neighbor_edges_per_atom"),
                    unit="neighbor_edges_per_atom",
                    direction="lower",
                    estimator="total Nequix neighbor edges divided by processed atoms",
                    sample_count=records,
                ),
                coordinate(
                    name="processed_atom_budget",
                    definition_uri=f"{CONVENTION_URI}#processed_atom_budget",
                    definition_revision="v2-frozen",
                    role="cost",
                    value=float(candidate["atoms"]),
                    unit="processed_atoms",
                    direction="contextual",
                    estimator="sum of atom instances across retained structures",
                    sample_count=records,
                ),
            ],
            artifacts=artifacts,
            attributes={
                "source_family": source_family,
                "selection_rule": selection_rule,
                "records": records,
                "parents": candidate["parents"],
                "chemical_systems": candidate["chemical_systems"],
                "parent_prototypes": candidate["parent_prototypes"],
                "membership_sha256": candidate["membership_sha256"],
                "panel_role": candidate["role"],
                "ranked_prefix_fraction": candidate["ranked_prefix_fraction"],
                "candidate_panel_status": bank["status"],
            },
        )
        profiles.append(profile)

    for output, profile in zip(outputs, profiles, strict=True):
        write_profile_input(output, profile, force=force)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--overlap", type=Path, default=DEFAULT_OVERLAP)
    parser.add_argument("--target-roles", type=Path, default=DEFAULT_TARGET_ROLES)
    parser.add_argument("--pool", type=Path, default=DEFAULT_POOL)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--candidate-id", action="append", dest="candidate_ids")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    outputs = export_profiles(
        bank_path=args.bank,
        validation_path=args.validation,
        source_path=args.source,
        checkpoint_path=args.checkpoint,
        overlap_path=args.overlap,
        target_roles_path=args.target_roles,
        pool_path=args.pool,
        output_dir=args.output_dir,
        candidate_ids=args.candidate_ids,
        force=args.force,
    )
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
