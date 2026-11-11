"""Qualification for native Q07820 reaction-bank bundles."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any


class MolecularSourceError(ValueError):
    """Raised when a molecular source does not satisfy the released contract."""


SOURCE_FORMAT = "rxnflow-q07820-qualified-bank-v4"
STUDY = "prospective-reaction-environment-selection"
TARGET = "Q07820"
BANKS = {
    "hash_uniform",
    "reward_signal",
    "validity_cost",
    "scaffold_coverage",
    "route_coverage",
    "graph_embedding_coverage",
}
COORDINATES = {
    "mean_target_reward",
    "mean_generated_action_count",
    "mean_oracle_seconds",
    "unique_scaffold_fraction",
    "unique_ring_systems_per_record",
    "unique_route_fraction",
    "unique_reaction_families",
    "embedding_mean_nearest_neighbor_distance",
}
REQUIRED_FILES = (
    "BANK_CONSTRUCTION_CONTRACT_V4.json",
    "DEVELOPMENT_BANK_QUALIFICATION_V4.json",
    "MEASUREMENT_CONTRACT_V4.json",
    "MEASUREMENT_RELIABILITY_RESULT_V3.json",
    "MOLGENBENCH_ARCHIVE_AUDIT.json",
    "ORACLE_QUALIFICATION.json",
    "PROTOCOL.json",
    "SOURCE_AUDIT.json",
    "TARGET_FIXTURE_AUDIT.json",
    "TARGET_REWARD_CONTRACT_V3.json",
    "TARGET_SELECTION_RESULT.json",
    "WARM_START_QUALIFICATION.json",
)


def _read(root: Path, name: str) -> dict[str, Any]:
    path = root / name
    if not path.is_file():
        raise MolecularSourceError(f"required molecular source artifact is missing: {name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise MolecularSourceError(
            f"cannot read molecular source artifact {name}: {error}"
        ) from error
    if not isinstance(value, dict):
        raise MolecularSourceError(f"molecular source artifact is not an object: {name}")
    return value


def bundle_digest(root: Path) -> str:
    """Return the deterministic digest of the contract-bearing bundle files."""

    if not root.is_dir():
        raise MolecularSourceError(f"molecular source is not a directory: {root}")
    digest = hashlib.sha256()
    for name in REQUIRED_FILES:
        path = root / name
        if not path.is_file():
            raise MolecularSourceError(f"required molecular source artifact is missing: {name}")
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MolecularSourceError(message)


def _is_sha256(value: object) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", str(value)))


def _is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def qualify_bundle(root: Path) -> dict[str, Any]:
    """Validate a Q07820 bank bundle without running measurement or training."""

    values = {name: _read(root, name) for name in REQUIRED_FILES}
    bank_contract = values["BANK_CONSTRUCTION_CONTRACT_V4.json"]
    result = values["DEVELOPMENT_BANK_QUALIFICATION_V4.json"]
    measurement_contract = values["MEASUREMENT_CONTRACT_V4.json"]
    measurement = values["MEASUREMENT_RELIABILITY_RESULT_V3.json"]
    warm_start = values["WARM_START_QUALIFICATION.json"]
    target_selection = values["TARGET_SELECTION_RESULT.json"]
    source_audit = values["SOURCE_AUDIT.json"]
    archive = values["MOLGENBENCH_ARCHIVE_AUDIT.json"]
    fixtures = values["TARGET_FIXTURE_AUDIT.json"]
    oracle = values["ORACLE_QUALIFICATION.json"]
    reward = values["TARGET_REWARD_CONTRACT_V3.json"]
    protocol = values["PROTOCOL.json"]

    _require(result.get("schema_version") == "4.0", "bank qualification is not version 4")
    _require(result.get("study") == STUDY, "bank qualification belongs to another study")
    _require(result.get("qualification") == "pass", "bank qualification did not pass")
    _require(bank_contract.get("schema_version") == "4.0", "bank contract is not version 4")
    _require(
        measurement_contract.get("schema_version") == "4.0",
        "measurement contract is not version 4",
    )
    _require(result.get("bank_size") == bank_contract.get("bank_size") == 512, "bank size changed")
    memberships = result.get("construction_memberships", {})
    confirmation = result.get("confirmation_reconstruction_memberships", {})
    summaries = result.get("summaries", [])
    _require(set(memberships) == BANKS, "construction bank set is incomplete")
    _require(set(confirmation) == BANKS, "confirmation bank set is incomplete")
    _require(len(summaries) == 2, "both independent bank summary views are required")
    for bank in BANKS:
        members = memberships[bank]
        confirmed = confirmation[bank]
        _require(
            len(members) == len(set(members)) == 512 and all(_is_sha256(item) for item in members),
            f"{bank} construction membership is incomplete or invalid",
        )
        _require(
            len(confirmed) == len(set(confirmed)) == 512
            and all(_is_sha256(item) for item in confirmed),
            f"{bank} confirmation membership is incomplete or invalid",
        )
        for view in summaries:
            coordinates = view.get(bank, {})
            _require(set(coordinates) == COORDINATES, f"{bank} coordinates are incomplete")
            _require(
                all(_is_finite_number(value) for value in coordinates.values()),
                f"{bank} coordinates contain missing or non-finite values",
            )

    checks = result.get("confirmation_checks", {})
    _require(checks and all(value is True for value in checks.values()), "selector fidelity failed")
    _require(measurement.get("qualification") == "pass", "measurement reliability did not pass")
    per_view_checks = measurement.get("per_view_checks", [])
    _require(
        len(per_view_checks) == 2
        and all(checks and all(checks.values()) for checks in per_view_checks),
        "a measurement view contains a failed gate",
    )
    _require(
        measurement.get("two_view_checks") and all(measurement["two_view_checks"].values()),
        "cross-view measurement reliability failed",
    )
    _require(
        len(measurement.get("views", [])) == 2
        and all(view.get("oracle_completion_fraction") == 1.0 for view in measurement["views"]),
        "oracle measurement is incomplete or infrastructure-invalid",
    )
    for view in measurement["views"]:
        attempts = view.get("attempts")
        _require(
            isinstance(attempts, int)
            and attempts > 0
            and view.get("returned_records") == attempts
            and view.get("returned_valid_fraction") == 1.0
            and view.get("finite_graph_embeddings") is True
            and isinstance(view.get("unique_canonical_products"), int)
            and view["unique_canonical_products"] > 0
            and view.get("reaction_family_counts")
            and all(count > 0 for count in view["reaction_family_counts"].values()),
            "chemistry measurement contains missing or invalid records",
        )

    policy = warm_start.get("artifacts", {}).get("weights_only_starting_policy", {})
    _require(warm_start.get("qualification") == "pass", "starting policy did not qualify")
    _require(_is_sha256(policy.get("sha256")), "starting-policy revision is missing or invalid")
    _require(
        target_selection.get("decision") == "select"
        and target_selection.get("selected_target") == TARGET
        and reward.get("selected_target") == TARGET,
        "selected target is missing or inconsistent",
    )
    _require(reward.get("schema_version") == "3.0", "target reward contract is not version 3")

    rxnflow = source_audit.get("rxnflow", {})
    molgenbench = source_audit.get("molgenbench", {})
    _require(source_audit.get("study") == STUDY, "source audit belongs to another study")
    _require(
        source_audit.get("training_or_evaluation_outcomes_inspected") is False,
        "source audit opened training or evaluation outcomes",
    )
    _require(rxnflow.get("qualification") == "pass", "RxnFlow source audit did not pass")
    _require(
        bool(re.fullmatch(r"[0-9a-f]{40}", str(rxnflow.get("commit", "")))),
        "RxnFlow revision is missing or invalid",
    )
    _require(
        molgenbench.get("qualification") in {"code_pass_dataset_open", "pass"},
        "MolGenBench source audit did not pass",
    )
    _require(
        bool(re.fullmatch(r"[0-9a-f]{40}", str(molgenbench.get("commit", "")))),
        "MolGenBench revision is missing or invalid",
    )
    archive_sha = archive.get("archive", {}).get("sha256")
    _require(
        archive.get("qualification") == "archive_metadata_pass_target_contents_open",
        "MolGenBench archive audit did not pass",
    )
    _require(_is_sha256(archive_sha), "MolGenBench archive revision is missing or invalid")
    _require(
        fixtures.get("qualification") == "target_fixture_structure_pass_oracle_behavior_open",
        "target-fixture audit did not pass",
    )
    _require(
        fixtures.get("archive_sha256") == archive_sha,
        "target fixtures are not bound to the audited archive",
    )
    fixture = next(
        (item for item in fixtures.get("targets", []) if item.get("target_id") == TARGET), None
    )
    _require(
        fixture is not None and fixture.get("fixture_integrity") == "pass",
        "Q07820 target fixtures did not pass integrity",
    )
    oracle_target = next(
        (item for item in oracle.get("targets", []) if item.get("target_id") == TARGET), None
    )
    _require(oracle.get("qualification") == "pass", "docking oracle did not qualify")
    _require(
        oracle_target is not None and oracle_target.get("qualification") == "pass",
        "Q07820 oracle did not qualify",
    )
    _require(
        oracle.get("sealed_boundary", {}).get("training_or_evaluation_outcomes_opened") is False,
        "oracle qualification opened downstream outcomes",
    )
    sealed = protocol.get("sealed_boundary", {})
    _require(
        sealed.get("training_or_evaluation_outcomes_inspected") is False,
        "protocol opened training or evaluation outcomes",
    )
    _require(
        sealed.get("candidate_training_outcomes_exist") is False,
        "candidate-training outcomes already exist",
    )
    _require(
        reward.get("sealed_boundary", {}).get("development_training_started") is False,
        "development training already started",
    )

    return {
        "target_id": TARGET,
        "bank_count": len(BANKS),
        "bank_size": 512,
        "measurement_views": len(measurement["views"]),
        "starting_policy_sha256": f"sha256:{policy['sha256']}",
        "rxnflow_revision": rxnflow["commit"],
        "molgenbench_revision": molgenbench["commit"],
        "archive_sha256": f"sha256:{archive_sha}",
        "training_outcomes_opened": False,
    }
