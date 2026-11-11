"""Qualification for a portable atomistic candidate-bank source."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


class NativeSourceError(ValueError):
    """Raised when an atomistic candidate bank violates its source contract."""


BANK_FIELDS = {
    "bank_id",
    "claim_bank",
    "claim_boundary",
    "exclusions",
    "measurement_contract",
    "properties",
    "purpose",
    "records",
    "schema_version",
    "source",
    "starting_checkpoint",
    "target",
}
RECORD_FIELDS = {
    "atomic_numbers",
    "cell_angstrom",
    "composition_reduced",
    "energy_ev",
    "fidelity",
    "forces_ev_per_angstrom",
    "material_id",
    "neighbor_edges",
    "parent_prototype",
    "pbc",
    "positions_angstrom",
    "record_id",
    "record_status",
    "source_family",
    "source_row_id",
    "stress_ev_per_angstrom3",
}
RECORD_STATUSES = {"valid", "scientific_zero", "unstable", "infrastructure_failure"}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _object(value: Any, field: str, expected: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise NativeSourceError(f"{field} has unknown or missing fields")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NativeSourceError(f"{field} must be non-empty text")
    return value.strip()


def _integer(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise NativeSourceError(f"{field} must be an integer at least {minimum}")
    return value


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise NativeSourceError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise NativeSourceError(f"{field} must be finite")
    return result


def _vector(value: Any, field: str, length: int) -> list[float]:
    if not isinstance(value, list) or len(value) != length:
        raise NativeSourceError(f"{field} must contain {length} values")
    return [_number(item, f"{field}[{index}]") for index, item in enumerate(value)]


def _matrix(value: Any, field: str, rows: int, columns: int) -> list[list[float]]:
    if not isinstance(value, list) or len(value) != rows:
        raise NativeSourceError(f"{field} must contain {rows} rows")
    return [_vector(row, f"{field}[{index}]", columns) for index, row in enumerate(value)]


def _determinant_3x3(matrix: list[list[float]]) -> float:
    return (
        matrix[0][0] * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
        - matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
        + matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0])
    )


def _load_json(path: Path, field: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise NativeSourceError(f"cannot read {field}: {error}") from error
    if not isinstance(value, dict):
        raise NativeSourceError(f"{field} must contain one JSON object")
    return value


def _validate_bank_contract(bank: dict[str, Any], source_license: str) -> None:
    _object(bank, "bank", BANK_FIELDS)
    if bank["schema_version"] != "anarres.materials-atomistic-bank.v1":
        raise NativeSourceError("unsupported atomistic bank schema")
    if bank["purpose"] != "source_qualification_only":
        raise NativeSourceError("portable fixture must be marked source_qualification_only")

    records = _object(
        bank["records"],
        "records",
        {"atoms", "count", "neighbor_edges", "path", "sha256"},
    )
    _integer(records["count"], "records.count", minimum=1)
    _integer(records["atoms"], "records.atoms", minimum=1)
    _integer(records["neighbor_edges"], "records.neighbor_edges")
    if Path(_text(records["path"], "records.path")).name != records["path"]:
        raise NativeSourceError("records.path must name a file beside bank.json")
    if len(_text(records["sha256"], "records.sha256")) != 64:
        raise NativeSourceError("records.sha256 must be a SHA-256 digest")

    source = _object(
        bank["source"],
        "source",
        {
            "archive_bytes",
            "archive_sha256",
            "archive_url",
            "dataset",
            "license",
            "revision",
            "source_families",
            "split",
        },
    )
    if _text(source["license"], "source.license") != source_license:
        raise NativeSourceError("manifest license does not match the bank source license")
    _integer(source["archive_bytes"], "source.archive_bytes", minimum=1)
    if len(_text(source["archive_sha256"], "source.archive_sha256")) != 64:
        raise NativeSourceError("source.archive_sha256 must be a SHA-256 digest")
    if not _text(source["archive_url"], "source.archive_url").startswith("https://"):
        raise NativeSourceError("source.archive_url must be an immutable HTTPS reference")
    if source["split"] != "train":
        raise NativeSourceError("candidate records must come from the pinned train split")
    families = source["source_families"]
    if (
        not isinstance(families, list)
        or not families
        or any(not isinstance(x, str) for x in families)
    ):
        raise NativeSourceError("source.source_families must be a non-empty text list")
    if len(families) != len(set(families)):
        raise NativeSourceError("source.source_families contains duplicates")

    properties = _object(
        bank["properties"],
        "properties",
        {"energy_unit", "fidelity", "force_unit", "required", "stress_unit"},
    )
    expected_units = {
        "energy_unit": "eV",
        "force_unit": "eV/angstrom",
        "stress_unit": "eV/angstrom^3",
    }
    for field, expected in expected_units.items():
        if properties[field] != expected:
            raise NativeSourceError(f"properties.{field} must be '{expected}'")
    if properties["required"] != ["energy", "forces", "stress"]:
        raise NativeSourceError("properties.required must contain energy, forces, and stress")

    checkpoint = _object(
        bank["starting_checkpoint"],
        "starting_checkpoint",
        {"license", "name", "sha256"},
    )
    if checkpoint["name"] != "Nequix-MP-1":
        raise NativeSourceError("starting checkpoint must be Nequix-MP-1")
    checkpoint_digest = _text(checkpoint["sha256"], "starting_checkpoint.sha256")
    if len(checkpoint_digest) != 64:
        raise NativeSourceError("starting_checkpoint.sha256 must be a SHA-256 digest")

    contract = _object(
        bank["measurement_contract"],
        "measurement_contract",
        {
            "calculator",
            "neighbor_list",
            "required_calculator_revision",
            "required_starting_checkpoint_sha256",
        },
    )
    calculator = _object(
        contract["calculator"],
        "measurement_contract.calculator",
        {"name", "repository", "revision", "version"},
    )
    if calculator["name"] != "Nequix" or calculator["version"] != "0.4.5":
        raise NativeSourceError("measurement calculator must be Nequix 0.4.5")
    if calculator["revision"] != contract["required_calculator_revision"]:
        raise NativeSourceError("calculator revision does not match the measurement contract")
    if checkpoint_digest != contract["required_starting_checkpoint_sha256"]:
        raise NativeSourceError("starting checkpoint does not match the measurement contract")
    _object(
        contract["neighbor_list"],
        "measurement_contract.neighbor_list",
        {"edge_count_field", "implementation", "preprocessing"},
    )
    if contract["neighbor_list"]["edge_count_field"] != "neighbor_edges":
        raise NativeSourceError("neighbor-list contract must use neighbor_edges")

    target = _object(
        bank["target"],
        "target",
        {"dataset", "evaluation_only", "license", "property", "unit"},
    )
    if target["evaluation_only"] is not True or target["unit"] != "THz":
        raise NativeSourceError("phonon target must remain evaluation-only with THz units")

    exclusions = _object(
        bank["exclusions"],
        "exclusions",
        {"evaluation_material_ids", "evaluation_material_ids_sha256", "target_roles_sha256"},
    )
    evaluation_ids = exclusions["evaluation_material_ids"]
    if not isinstance(evaluation_ids, list) or any(not isinstance(x, str) for x in evaluation_ids):
        raise NativeSourceError("exclusions.evaluation_material_ids must be a text list")
    if len(evaluation_ids) != len(set(evaluation_ids)):
        raise NativeSourceError("evaluation material exclusions contain duplicates")
    digest = hashlib.sha256(("\n".join(sorted(evaluation_ids)) + "\n").encode()).hexdigest()
    if digest != exclusions["evaluation_material_ids_sha256"]:
        raise NativeSourceError("evaluation material exclusion digest does not match its members")

    claim_bank = _object(
        bank["claim_bank"],
        "claim_bank",
        {
            "atoms",
            "construction_script_sha256",
            "manifest_sha256",
            "neighbor_edges",
            "overlap_audit_sha256",
            "records",
            "role",
            "selection",
            "source_archive_sha256",
            "source_archive_url",
        },
    )
    if claim_bank["role"] != "deterministic_immutable_derivation":
        raise NativeSourceError("claim bank must remain a deterministic immutable derivation")
    for field in ("records", "atoms", "neighbor_edges"):
        _integer(claim_bank[field], f"claim_bank.{field}", minimum=1)
    if len(_text(claim_bank["manifest_sha256"], "claim_bank.manifest_sha256")) != 64:
        raise NativeSourceError("claim_bank.manifest_sha256 must be a SHA-256 digest")
    for field in (
        "construction_script_sha256",
        "overlap_audit_sha256",
        "source_archive_sha256",
    ):
        if len(_text(claim_bank[field], f"claim_bank.{field}")) != 64:
            raise NativeSourceError(f"claim_bank.{field} must be a SHA-256 digest")
    if claim_bank["source_archive_sha256"] != source["archive_sha256"]:
        raise NativeSourceError("claim-bank archive digest does not match the source archive")
    if claim_bank["source_archive_url"] != source["archive_url"]:
        raise NativeSourceError("claim-bank archive URL does not match the source archive")
    selection = _object(
        claim_bank["selection"],
        "claim_bank.selection",
        {
            "maximum_records_per_parent",
            "oversample_factor",
            "records_per_source_family",
            "salt",
            "source_families",
            "supported_atomic_numbers",
        },
    )
    for field in ("maximum_records_per_parent", "oversample_factor", "records_per_source_family"):
        _integer(selection[field], f"claim_bank.selection.{field}", minimum=1)
    claim_families = selection["source_families"]
    if (
        not isinstance(claim_families, list)
        or not claim_families
        or any(not isinstance(item, str) or not item for item in claim_families)
        or len(claim_families) != len(set(claim_families))
    ):
        raise NativeSourceError("claim_bank.selection.source_families must be unique text")
    _text(selection["salt"], "claim_bank.selection.salt")
    _text(selection["supported_atomic_numbers"], "claim_bank.selection.supported_atomic_numbers")
    if (
        selection["records_per_source_family"] * len(selection["source_families"])
        != claim_bank["records"]
    ):
        raise NativeSourceError("claim-bank selection does not produce the declared record count")

    boundary = _object(
        bank["claim_boundary"],
        "claim_boundary",
        {
            "candidate_training_outcomes_opened",
            "fixture_role",
            "policy_probe_available",
            "policy_probe_blocker",
        },
    )
    if boundary["candidate_training_outcomes_opened"] is not False:
        raise NativeSourceError("source qualification cannot open candidate training outcomes")
    if boundary["fixture_role"] != "source_qualification_only":
        raise NativeSourceError("fixture role must preserve the qualification boundary")
    if boundary["policy_probe_available"] is not False:
        raise NativeSourceError("portable policy probing is not released for this source format")


def _validate_record(
    record: dict[str, Any],
    *,
    index: int,
    fidelity: str,
    source_families: set[str],
    evaluation_material_ids: set[str],
) -> tuple[str, str, int, int, str]:
    prefix = f"record {index}"
    _object(record, prefix, RECORD_FIELDS)
    record_id = _text(record["record_id"], f"{prefix}.record_id")
    material_id = _text(record["material_id"], f"{prefix}.material_id")
    if material_id in evaluation_material_ids:
        raise NativeSourceError(f"{record_id} overlaps an evaluation material identity")
    status = _text(record["record_status"], f"{prefix}.record_status")
    if status not in RECORD_STATUSES:
        raise NativeSourceError(f"{record_id} has unsupported record_status '{status}'")
    if status == "infrastructure_failure":
        raise NativeSourceError(f"{record_id} is an infrastructure failure")

    atomic_numbers = record["atomic_numbers"]
    if not isinstance(atomic_numbers, list) or not atomic_numbers:
        raise NativeSourceError(f"{record_id} has no atoms")
    for atom_index, atomic_number in enumerate(atomic_numbers):
        _integer(atomic_number, f"{prefix}.atomic_numbers[{atom_index}]", minimum=1)
        if atomic_number > 118:
            raise NativeSourceError(f"{record_id} has an invalid atomic number")
    atom_count = len(atomic_numbers)

    cell = _matrix(record["cell_angstrom"], f"{prefix}.cell_angstrom", 3, 3)
    if abs(_determinant_3x3(cell)) <= 1e-12:
        raise NativeSourceError(f"{record_id} has a singular unit cell")
    _matrix(record["positions_angstrom"], f"{prefix}.positions_angstrom", atom_count, 3)
    _matrix(
        record["forces_ev_per_angstrom"],
        f"{prefix}.forces_ev_per_angstrom",
        atom_count,
        3,
    )
    _vector(record["stress_ev_per_angstrom3"], f"{prefix}.stress_ev_per_angstrom3", 6)
    _number(record["energy_ev"], f"{prefix}.energy_ev")
    pbc = record["pbc"]
    if not isinstance(pbc, list) or len(pbc) != 3 or any(type(item) is not bool for item in pbc):
        raise NativeSourceError(f"{record_id} has invalid periodic boundary flags")
    if not all(pbc):
        raise NativeSourceError(f"{record_id} must be periodic in all three directions")

    if record["fidelity"] != fidelity:
        raise NativeSourceError(f"{record_id} has the wrong fidelity")
    source_family = _text(record["source_family"], f"{prefix}.source_family")
    if source_family not in source_families:
        raise NativeSourceError(f"{record_id} has an unpinned source family")
    _integer(record["source_row_id"], f"{prefix}.source_row_id")
    edges = _integer(record["neighbor_edges"], f"{prefix}.neighbor_edges")
    _text(record["composition_reduced"], f"{prefix}.composition_reduced")
    _text(record["parent_prototype"], f"{prefix}.parent_prototype")
    return record_id, material_id, atom_count, edges, status


def qualify_atomistic_bank(
    source: Path,
    *,
    expected_revision: str,
    source_license: str,
) -> dict[str, Any]:
    """Validate one portable bank without running a model or opening outcomes."""

    root = source.resolve()
    if not root.is_dir():
        raise NativeSourceError(f"atomistic bank source must be a directory: {root}")
    bank_path = root / "bank.json"
    if not bank_path.is_file():
        raise NativeSourceError(f"atomistic bank metadata is missing: {bank_path}")
    observed_bank_digest = file_sha256(bank_path)
    if expected_revision != f"sha256:{observed_bank_digest}":
        raise NativeSourceError("manifest source revision does not match bank.json")
    bank = _load_json(bank_path, "bank.json")
    _validate_bank_contract(bank, source_license)

    records_path = root / bank["records"]["path"]
    if not records_path.is_file():
        raise NativeSourceError(f"atomistic record file is missing: {records_path}")
    observed_records_digest = file_sha256(records_path)
    if observed_records_digest != bank["records"]["sha256"]:
        raise NativeSourceError("atomistic record content digest does not match bank.json")

    records: list[dict[str, Any]] = []
    try:
        for line_number, line in enumerate(
            records_path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                raise NativeSourceError(f"structures.jsonl contains a blank line at {line_number}")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise NativeSourceError(f"structures.jsonl line {line_number} is not an object")
            records.append(value)
    except (OSError, json.JSONDecodeError) as error:
        raise NativeSourceError(f"cannot read structures.jsonl: {error}") from error

    source_families = set(bank["source"]["source_families"])
    evaluation_ids = set(bank["exclusions"]["evaluation_material_ids"])
    record_ids: list[str] = []
    material_ids: list[str] = []
    atoms = 0
    edges = 0
    statuses = {status: 0 for status in sorted(RECORD_STATUSES)}
    observed_families: set[str] = set()
    for index, record in enumerate(records):
        record_id, material_id, atom_count, edge_count, status = _validate_record(
            record,
            index=index,
            fidelity=bank["properties"]["fidelity"],
            source_families=source_families,
            evaluation_material_ids=evaluation_ids,
        )
        record_ids.append(record_id)
        material_ids.append(material_id)
        atoms += atom_count
        edges += edge_count
        statuses[status] += 1
        observed_families.add(record["source_family"])
    if len(record_ids) != len(set(record_ids)):
        raise NativeSourceError("atomistic bank contains duplicate record identities")
    if len(material_ids) != len(set(material_ids)):
        raise NativeSourceError("qualification slice contains duplicate material identities")
    if observed_families != source_families:
        raise NativeSourceError("source family declaration does not match the record content")
    expected_totals = bank["records"]
    if len(records) != expected_totals["count"]:
        raise NativeSourceError("record count does not match bank.json")
    if atoms != expected_totals["atoms"]:
        raise NativeSourceError("atom total does not match bank.json")
    if edges != expected_totals["neighbor_edges"]:
        raise NativeSourceError("neighbor-edge total does not match bank.json")

    membership_digest = hashlib.sha256(("\n".join(sorted(record_ids)) + "\n").encode()).hexdigest()
    return {
        "status": "qualified",
        "bank_id": bank["bank_id"],
        "purpose": bank["purpose"],
        "records": len(records),
        "materials": len(set(material_ids)),
        "atoms": atoms,
        "neighbor_edges": edges,
        "record_status_counts": statuses,
        "source_families": sorted(observed_families),
        "membership_sha256": f"sha256:{membership_digest}",
        "content_sha256": f"sha256:{observed_records_digest}",
        "bank_sha256": f"sha256:{observed_bank_digest}",
        "claim_bank": bank["claim_bank"],
        "starting_checkpoint": bank["starting_checkpoint"],
        "target": bank["target"],
        "policy_probe_available": False,
        "policy_probe_blocker": bank["claim_boundary"]["policy_probe_blocker"],
        "training_started": False,
        "candidate_outcomes_opened": False,
    }
