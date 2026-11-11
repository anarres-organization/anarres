"""Static qualification for practitioner-supplied molecular environments."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


class MolecularSourceError(ValueError):
    """Raised when a molecular source does not satisfy its native contract."""


SOURCE_FORMAT = "rxnflow-molecular-environment-v1"
SOURCE_FILE = "molecular-source.json"
SCHEMA_VERSION = "anarres.molecular-environment-source.v1"
REPLAY_ARTIFACT = "anarres.rxnflow-replay-bank.v1"
REQUIRED_CONTRACTS = {"oracle", "filters", "docking", "probe"}
REQUIRED_ENDPOINT_ASSETS = {
    "pocket",
    "protein",
    "reference_actives",
    "reference_interaction_scores",
    "thresholds",
}
REQUIRED_OUTCOME_STATES = {
    "scientific_zero",
    "filter_rejection",
    "invalid_chemistry",
    "docking_failure",
    "timeout",
    "missing_score",
    "infrastructure_failure",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_digest(root: Path) -> str:
    """Hash one directory without following links or depending on metadata."""

    if not root.is_dir():
        raise MolecularSourceError(f"expected a directory: {root}")
    digest = hashlib.sha256()
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if not files:
        raise MolecularSourceError(f"directory contains no files: {root}")
    for path in files:
        if path.is_symlink():
            raise MolecularSourceError(f"symbolic links are not allowed: {path}")
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def bundle_digest(root: Path) -> str:
    """Return the stable revision of one initialized source directory."""

    if not root.is_dir():
        raise MolecularSourceError(f"molecular source is not a directory: {root}")
    digest = hashlib.sha256()
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.relative_to(root).as_posix() != "anarres.toml"
    )
    if not files:
        raise MolecularSourceError("molecular source contains no native files")
    for path in files:
        if path.is_symlink():
            raise MolecularSourceError(f"symbolic links are not allowed: {path}")
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def _read_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise MolecularSourceError(f"{label} is missing: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise MolecularSourceError(f"cannot read {label}: {error}") from error
    if not isinstance(value, dict):
        raise MolecularSourceError(f"{label} must be a JSON object")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MolecularSourceError(message)


def _resolve(root: Path, value: object, label: str) -> Path:
    relative = Path(str(value))
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise MolecularSourceError(f"{label} must be a relative path inside the source")
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise MolecularSourceError(f"{label} escapes the source directory") from error
    return path


def _artifact(root: Path, value: object, label: str, *, directory: bool = False) -> Path:
    if not isinstance(value, dict):
        raise MolecularSourceError(f"{label} must describe a path and SHA-256 digest")
    path = _resolve(root, value.get("path"), f"{label} path")
    expected = value.get("sha256")
    _require(bool(re.fullmatch(r"[0-9a-f]{64}", str(expected))), f"{label} digest is invalid")
    if directory:
        observed = tree_digest(path)
    else:
        _require(path.is_file(), f"{label} is missing: {path}")
        observed = sha256_file(path)
    _require(observed == expected, f"{label} digest does not match its content")
    return path


def _balanced_smiles(value: str) -> bool:
    """Apply a portable syntax gate; native chemistry remains runtime-owned."""

    if not value or any(character.isspace() for character in value):
        return False
    if not re.fullmatch(r"[A-Za-z0-9@+\-\[\]()=#%\\/.:*]+", value):
        return False
    pairs = {"(": ")", "[": "]"}
    stack: list[str] = []
    for character in value:
        if character in pairs:
            stack.append(pairs[character])
        elif character in {")", "]"} and (not stack or stack.pop() != character):
            return False
    return not stack


def _building_blocks(path: Path, duplicate_policy: object) -> dict[str, str]:
    _require(
        duplicate_policy == "reject_exact_canonical_smiles",
        "duplicate policy must reject exact canonical-SMILES duplicates",
    )
    records: dict[str, str] = {}
    smiles_seen: set[str] = set()
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        fields = raw.split("\t")
        _require(len(fields) == 2, f"building-block row {number} must be SMILES<TAB>ID")
        smiles, identifier = (field.strip() for field in fields)
        _require(_balanced_smiles(smiles), f"building-block row {number} has malformed SMILES")
        _require(bool(identifier), f"building-block row {number} has no stable identity")
        _require(identifier not in records, f"duplicate building-block identity: {identifier}")
        _require(smiles not in smiles_seen, f"duplicate canonical SMILES: {smiles}")
        records[identifier] = smiles
        smiles_seen.add(smiles)
    _require(bool(records), "building-block source is empty")
    return records


def _reaction_templates(path: Path, block_ids: set[str]) -> dict[str, dict[str, Any]]:
    value = _read_object(path, "reaction-template source")
    rows = value.get("templates")
    _require(isinstance(rows, list) and rows, "reaction-template source has no templates")
    templates: dict[str, dict[str, Any]] = {}
    for row in rows:
        _require(isinstance(row, dict), "reaction template must be an object")
        identifier = str(row.get("template_id", "")).strip()
        _require(
            identifier and identifier not in templates, "reaction template identity is invalid"
        )
        _require(bool(str(row.get("reaction_smarts", "")).strip()), f"{identifier} lacks SMARTS")
        compatible = row.get("compatible_building_block_ids")
        _require(
            isinstance(compatible, list) and compatible, f"{identifier} has no compatibility set"
        )
        _require(
            len(compatible) == len(set(compatible)) and set(compatible) <= block_ids,
            f"{identifier} names missing or duplicate building blocks",
        )
        templates[identifier] = row
    return templates


def _replay_bank(
    path: Path,
    expected_count: object,
    expected_membership: object,
    block_ids: set[str],
    template_ids: set[str],
) -> tuple[list[str], set[str]]:
    value = _read_object(path, "candidate replay bank")
    _require(value.get("artifact_type") == REPLAY_ARTIFACT, "replay artifact type is unsupported")
    rows = value.get("items")
    _require(isinstance(rows, list) and rows, "candidate replay bank is empty")
    _require(expected_count == len(rows), "candidate replay item count does not match")
    trajectory_ids: list[str] = []
    molecule_ids: set[str] = set()
    for row in rows:
        _require(isinstance(row, dict), "replay item must be an object")
        trajectory_id = str(row.get("trajectory_id", "")).strip()
        molecule_id = str(row.get("molecule_id", "")).strip()
        smiles = str(row.get("canonical_smiles", "")).strip()
        _require(trajectory_id and molecule_id, "replay item lacks a stable identity")
        _require(_balanced_smiles(smiles), f"replay item {trajectory_id} has malformed SMILES")
        _require(
            set(row.get("building_block_ids", [])) <= block_ids,
            f"replay item {trajectory_id} names an unknown building block",
        )
        _require(
            set(row.get("reaction_template_ids", [])) <= template_ids,
            f"replay item {trajectory_id} names an unknown reaction template",
        )
        trajectory_ids.append(trajectory_id)
        molecule_ids.add(molecule_id)
    _require(len(trajectory_ids) == len(set(trajectory_ids)), "replay trajectory identities repeat")
    membership = hashlib.sha256(
        ("\n".join(sorted(trajectory_ids)) + "\n").encode("utf-8")
    ).hexdigest()
    _require(membership == expected_membership, "replay membership digest does not match")
    return trajectory_ids, molecule_ids


def load_source(root: Path) -> dict[str, Any]:
    """Load the native source declaration without qualifying its artifacts."""

    return _read_object(root / SOURCE_FILE, "molecular source declaration")


def qualify_source(root: Path) -> dict[str, Any]:
    """Qualify source inputs without sampling a policy or running docking."""

    source = load_source(root)
    _require(source.get("schema_version") == SCHEMA_VERSION, "source schema is unsupported")
    environment_id = str(source.get("environment_id", "")).strip()
    target_id = str(source.get("target_id", "")).strip()
    _require(environment_id and target_id, "source identities are incomplete")

    reaction = source.get("reaction_environment")
    _require(isinstance(reaction, dict), "reaction environment is missing")
    blocks_path = _artifact(root, reaction.get("building_blocks"), "building blocks")
    templates_path = _artifact(root, reaction.get("reaction_templates"), "reaction templates")
    prepared_path = _artifact(
        root, reaction.get("prepared_environment"), "prepared reaction environment", directory=True
    )
    report_path = _artifact(root, reaction.get("preparation_report"), "preparation report")
    blocks = _building_blocks(blocks_path, source.get("duplicate_policy"))
    templates = _reaction_templates(templates_path, set(blocks))
    preparation = _read_object(report_path, "preparation report")
    _require(preparation.get("status") == "qualified", "reaction environment did not qualify")
    _require(
        preparation.get("building_blocks_sha256") == sha256_file(blocks_path)
        and preparation.get("reaction_templates_sha256") == sha256_file(templates_path)
        and preparation.get("prepared_environment_sha256") == tree_digest(prepared_path),
        "preparation report is not bound to the supplied reaction environment",
    )
    _require(
        preparation.get("building_block_count") == len(blocks)
        and preparation.get("reaction_template_count") == len(templates),
        "preparation report counts do not match the native sources",
    )

    replay_spec = source.get("candidate_replay_bank")
    _require(isinstance(replay_spec, dict), "candidate replay bank is missing")
    replay_path = _artifact(root, replay_spec, "candidate replay bank")
    trajectory_ids, molecule_ids = _replay_bank(
        replay_path,
        replay_spec.get("item_count"),
        replay_spec.get("membership_sha256"),
        set(blocks),
        set(templates),
    )
    _require(
        replay_spec.get("duplicate_molecule_policy") == "retain_distinct_trajectory_ids",
        "candidate replay bank must declare duplicate-molecule handling",
    )

    policy = source.get("starting_policy")
    _require(isinstance(policy, dict), "starting policy is missing")
    policy_path = _artifact(root, policy, "starting policy")
    policy_id = str(policy.get("policy_id", "")).strip()
    _require(
        policy_id and policy.get("revision") == f"sha256:{sha256_file(policy_path)}",
        "policy identity is invalid",
    )

    target = source.get("target")
    _require(isinstance(target, dict), "prepared target is missing")
    target_root = _artifact(root, target.get("prepared_target"), "prepared target", directory=True)
    target_manifest_path = _resolve(target_root, target.get("manifest"), "target manifest")
    target_manifest = _read_object(target_manifest_path, "target manifest")
    _require(target_manifest.get("target_id") == target_id, "prepared target identity changed")
    fixture_fields = (
        ("receptor_pdbqt", "prepared_receptor"),
        ("reference_ligand", "reference_ligand"),
    )
    for field, digest_field in fixture_fields:
        fixture = _resolve(target_root, target_manifest.get(field), f"target {field}")
        _require(fixture.is_file(), f"target fixture is missing: {field}")
        _require(
            sha256_file(fixture) == target_manifest.get("fixture_sha256", {}).get(digest_field),
            f"target fixture digest changed: {field}",
        )
    endpoint_assets = target.get("endpoint_assets")
    _require(
        isinstance(endpoint_assets, dict) and set(endpoint_assets) == REQUIRED_ENDPOINT_ASSETS,
        "prepared target endpoint asset set is incomplete",
    )
    for name in sorted(REQUIRED_ENDPOINT_ASSETS):
        _artifact(root, endpoint_assets[name], f"endpoint asset {name}")

    contracts = source.get("contracts")
    _require(
        isinstance(contracts, dict) and set(contracts) == REQUIRED_CONTRACTS,
        "runtime contract set is incomplete",
    )
    loaded_contracts: dict[str, dict[str, Any]] = {}
    for name in sorted(REQUIRED_CONTRACTS):
        contract_path = _artifact(root, contracts[name], f"{name} contract")
        contract = _read_object(contract_path, f"{name} contract")
        _require(contract.get("target_id") == target_id, f"{name} contract targets another system")
        loaded_contracts[name] = contract
    semantics = loaded_contracts["oracle"].get("failure_semantics", {})
    _require(
        isinstance(semantics.get("scientific_zero"), list)
        and semantics["scientific_zero"]
        and isinstance(semantics.get("infrastructure_failure"), list)
        and semantics["infrastructure_failure"]
        and semantics.get("missing_score") == "missing",
        "oracle failure semantics do not preserve scientific zero, "
        "infrastructure failure, and missing score",
    )
    _require(
        set(loaded_contracts["oracle"].get("outcome_states", [])) == REQUIRED_OUTCOME_STATES,
        "oracle contract does not preserve every required outcome state",
    )
    probe = loaded_contracts["probe"]
    _require(
        isinstance(probe.get("attempts"), int)
        and probe["attempts"] > 0
        and isinstance(probe.get("seed"), int)
        and isinstance(probe.get("batch_size"), int)
        and probe["batch_size"] > 0,
        "probe contract lacks a bounded deterministic sample",
    )

    partitions = source.get("partitions")
    _require(isinstance(partitions, dict), "train/evaluation partitions are missing")
    training_ids = set(partitions.get("training_ids", []))
    evaluation_ids = set(partitions.get("evaluation_attempt_ids", []))
    _require(
        training_ids == set(trajectory_ids), "training partition differs from replay membership"
    )
    _require(
        evaluation_ids and training_ids.isdisjoint(evaluation_ids),
        "training and evaluation identities overlap",
    )

    licenses = source.get("sources")
    _require(isinstance(licenses, list) and licenses, "source revisions and licenses are missing")
    covered: set[str] = set()
    for item in licenses:
        _require(isinstance(item, dict), "source provenance entry must be an object")
        _require(
            bool(str(item.get("name", "")).strip())
            and bool(str(item.get("revision", "")).strip())
            and bool(str(item.get("license", "")).strip()),
            "source provenance lacks a name, revision, or license",
        )
        paths = item.get("paths")
        _require(isinstance(paths, list) and paths, "source provenance has no artifact paths")
        for value in paths:
            _resolve(root, value, "licensed artifact")
            covered.add(str(value))
    required_licensed_paths = {
        str(reaction["building_blocks"]["path"]),
        str(reaction["reaction_templates"]["path"]),
        str(policy["path"]),
        str(target["prepared_target"]["path"]),
    }
    _require(
        required_licensed_paths <= covered,
        "not every native source is covered by a license record",
    )

    return {
        "environment_id": environment_id,
        "target_id": target_id,
        "building_block_count": len(blocks),
        "reaction_template_count": len(templates),
        "candidate_replay_items": len(trajectory_ids),
        "candidate_unique_molecules": len(molecule_ids),
        "starting_policy_id": policy_id,
        "starting_policy_revision": policy["revision"],
        "prepared_environment": str(prepared_path),
        "prepared_target": str(target_root),
        "probe_attempts": probe["attempts"],
        "probe_seed": probe["seed"],
        "scientific_zero_states": semantics["scientific_zero"],
        "infrastructure_failure_states": semantics["infrastructure_failure"],
        "preserved_outcome_states": sorted(REQUIRED_OUTCOME_STATES),
        "training_outcomes_opened": False,
        "probe_outcomes_opened": False,
    }
