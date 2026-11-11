"""CLI wrapper for the released MLIP candidate-measurement adapter."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

from anarres.core import consume_adapter_invocation, load_source_manifest

from anarres_materials_adapter.native_source import NativeSourceError, qualify_atomistic_bank


class MaterialsCliError(ValueError):
    """Raised when the released materials adapter cannot run."""


def adapter_descriptor() -> dict[str, Any]:
    """Describe the adapter without opening study artifacts."""

    return {
        "schema_version": "anarres.adapter-descriptor.v1",
        "name": "materials",
        "version": "0.7.0",
        "protocol_version": 2,
        "domain": "materials-interatomic-potentials",
        "executable": "anarres-materials",
        "profile_schema_versions": ["anarres.environment-profile-input.v1"],
        "capabilities": [
            "decision-protocol",
            "profile",
            "results",
            "source-qualification",
            "status",
            "verify",
        ],
        "measurement_contracts": [
            "materials.mlip-phonon-candidate-measurement.v2",
        ],
        "source_formats": ["atomistic-candidate-bank-v1"],
    }


def command_qualify_source(args: argparse.Namespace) -> dict[str, Any]:
    """Qualify one atomistic bank without probing, training, or opening outcomes."""

    descriptor = adapter_descriptor()
    source = load_source_manifest(
        args.manifest,
        expected_adapter="materials",
        expected_version=descriptor["version"],
        expected_domain=descriptor["domain"],
        accepted_formats=tuple(descriptor["source_formats"]),
    )
    report = qualify_atomistic_bank(
        source.source,
        expected_revision=source.revision,
        source_license=source.license,
    )
    return {
        "environment_id": source.environment_id,
        "native_format": source.native_format,
        "source_revision": source.revision,
        "source_license": source.license,
        **report,
    }


def repository_root(explicit: Path | None = None) -> Path:
    """Resolve a checkout containing the released study."""

    starts = [explicit.resolve()] if explicit is not None else [Path.cwd().resolve()]
    for start in starts:
        for candidate in (start, *start.parents):
            if exporter_path(candidate).is_file():
                return candidate
    raise MaterialsCliError(
        "Anarres repository not found. Run inside a checkout or pass --repository"
    )


def study_root(repository: Path) -> Path:
    return (
        repository
        / "experiments/ai-for-science/materials-science/mlip-phonon-environment-selection"
    )


def exporter_path(repository: Path) -> Path:
    return study_root(repository) / "export_environment_profiles.py"


def protocol_path(repository: Path) -> Path:
    return study_root(repository) / "DECISION_AND_REGRESSION_PROTOCOL.json"


def receipt_path(repository: Path) -> Path:
    return study_root(repository) / "PANEL_REGENERATION_RECEIPT.json"


def training_qualification_path(repository: Path) -> Path:
    return study_root(repository) / "TRAINING_QUALIFICATION_PROTOCOL.json"


def training_qualification_result_path(repository: Path) -> Path:
    return study_root(repository) / "TRAINING_QUALIFICATION_RESULT.json"


def starting_targets_path(repository: Path) -> Path:
    return study_root(repository) / "STARTING_CHECKPOINT_TARGETS.json"


def final_training_contract_path(repository: Path) -> Path:
    return study_root(repository) / "FINAL_TRAINING_CONTRACT.json"


def target_regression_features_path(repository: Path) -> Path:
    return study_root(repository) / "TARGET_REGRESSION_FEATURES.json"


def development_modeling_protocol_path(repository: Path) -> Path:
    return study_root(repository) / "DEVELOPMENT_MODELING_PROTOCOL.json"


def aggregate_fit_path(repository: Path) -> Path:
    return study_root(repository) / "AGGREGATE_UTILITY_FIT.json"


def regression_fit_path(repository: Path) -> Path:
    return study_root(repository) / "TARGET_REGRESSION_FIT.json"


def prospective_authorization_path(repository: Path) -> Path:
    return study_root(repository) / "PROSPECTIVE_TRAINING_AUTHORIZATION.json"


def prospective_outcomes_path(repository: Path) -> Path:
    return study_root(repository) / "PROSPECTIVE_OUTCOMES.json"


def prospective_score_path(repository: Path) -> Path:
    return study_root(repository) / "PROSPECTIVE_PREDICTION_SCORE.json"


def post_prospective_audit_path(repository: Path) -> Path:
    return study_root(repository) / "POST_PROSPECTIVE_AUDIT.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prospective_boundaries_opened(outcomes: dict[str, Any]) -> bool:
    boundary = outcomes.get("prospective_boundary")
    return isinstance(boundary, dict) and all(
        boundary.get(key) is True
        for key in (
            "prospective_candidate_training_outcomes_used",
            "prospective_target_outcomes_used",
        )
    )


def load_exporter(repository: Path) -> ModuleType:
    path = exporter_path(repository)
    if not path.is_file():
        raise MaterialsCliError(f"materials profile exporter is missing: {path}")
    specification = importlib.util.spec_from_file_location(
        "anarres_materials_mlip_profile_exporter", path
    )
    if specification is None or specification.loader is None:
        raise MaterialsCliError(f"cannot load materials profile exporter: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def command_status(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    exporter = load_exporter(repository)
    bank = exporter.read_object(exporter.DEFAULT_BANK)
    validation = exporter.read_object(exporter.DEFAULT_VALIDATION)
    protocol = exporter.read_object(protocol_path(repository))
    training_qualification = exporter.read_object(training_qualification_path(repository))
    training_result = exporter.read_object(training_qualification_result_path(repository))
    starting_targets = exporter.read_object(starting_targets_path(repository))
    final_contract = exporter.read_object(final_training_contract_path(repository))
    modeling_protocol = exporter.read_object(development_modeling_protocol_path(repository))
    authorization = exporter.read_object(prospective_authorization_path(repository))
    outcomes = exporter.read_object(prospective_outcomes_path(repository))
    score = exporter.read_object(prospective_score_path(repository))
    target_features_file = target_regression_features_path(repository)
    expected_target_features = modeling_protocol.get("inputs", {}).get(
        "target_regression_features_sha256"
    )
    modeling_protocol_frozen = (
        modeling_protocol.get("status") == "frozen_before_development_outcome_analysis"
    )
    target_features_bound = expected_target_features == sha256(target_features_file)
    target_features_frozen = modeling_protocol_frozen and target_features_bound
    candidates = bank.get("candidates")
    if not isinstance(candidates, list):
        raise MaterialsCliError("candidate panel has no candidate list")
    first_candidate = sorted(candidate["candidate_id"] for candidate in candidates)[0]
    with tempfile.TemporaryDirectory(prefix="anarres-materials-status-") as directory:
        output = exporter.export_profiles(
            output_dir=Path(directory), candidate_ids=[first_candidate]
        )[0]
        checks = {
            check["check_id"]: check
            for check in json.loads(output.read_text(encoding="utf-8"))["qualification_checks"]
        }
    return {
        "domain": "materials-interatomic-potentials",
        "candidate_panel_status": bank.get("status"),
        "candidate_count": len(candidates),
        "measurement_records": validation.get("records"),
        "measurements_complete": validation.get("status") == "complete",
        "candidate_outcomes_opened": prospective_boundaries_opened(outcomes),
        "final_training_panel_frozen": checks["final-panel-frozen"]["status"] == "pass",
        "decision_protocol_frozen": protocol.get("status")
        == "frozen_before_candidate_training_outcomes",
        "regression_protocol_frozen": "target_regression_prediction" in protocol,
        "training_qualification_protocol_status": training_qualification.get("status"),
        "training_qualification_status": training_result.get("status"),
        "selected_learning_rate": training_result.get("selected_learning_rate"),
        "starting_target_features_complete": starting_targets.get("status")
        == "complete_before_candidate_training",
        "final_training_contract_status": final_contract.get("status"),
        "target_regression_features_frozen": target_features_frozen,
        "development_modeling_protocol_frozen": modeling_protocol_frozen,
        "prospective_predictions_frozen": authorization.get("status")
        == "prospective_predictions_frozen",
        "prospective_test_status": score.get("status"),
        "predictive_evidence_available": score.get("status") == "prospective_test_scored",
        "native_source_format": "atomistic-candidate-bank-v1",
        "policy_probe_available": False,
        "policy_probe_blocker": (
            "Nequix checkpoint execution requires the native GPU and ASE-LMDB runtime."
        ),
        "next_gate": "freeze support-aware abstention and expand development support",
    }


def command_protocol(args: argparse.Namespace) -> dict[str, Any]:
    """Report the frozen pre-outcome decision and regression contract."""

    repository = repository_root(args.repository)
    exporter = load_exporter(repository)
    bank_path = exporter.DEFAULT_BANK
    protocol_file = protocol_path(repository)
    receipt_file = receipt_path(repository)
    training_file = training_qualification_path(repository)
    training_result_file = training_qualification_result_path(repository)
    starting_targets_file = starting_targets_path(repository)
    final_contract_file = final_training_contract_path(repository)
    target_features_file = target_regression_features_path(repository)
    modeling_protocol_file = development_modeling_protocol_path(repository)
    aggregate_file = aggregate_fit_path(repository)
    regression_file = regression_fit_path(repository)
    authorization_file = prospective_authorization_path(repository)
    bank = exporter.read_object(bank_path)
    protocol = exporter.read_object(protocol_file)
    receipt = exporter.read_object(receipt_file)
    training = exporter.read_object(training_file)
    training_result = exporter.read_object(training_result_file)
    starting_targets = exporter.read_object(starting_targets_file)
    final_contract = exporter.read_object(final_contract_file)
    target_features = exporter.read_object(target_features_file)
    modeling_protocol = exporter.read_object(modeling_protocol_file)
    aggregate = exporter.read_object(aggregate_file)
    regression = exporter.read_object(regression_file)
    authorization = exporter.read_object(authorization_file)

    expected_bank = protocol.get("inputs", {}).get("candidate_panel", {}).get("sha256")
    if expected_bank != sha256(bank_path):
        raise MaterialsCliError("decision protocol does not bind the released candidate panel")
    if receipt.get("original_artifact", {}).get("sha256") != expected_bank:
        raise MaterialsCliError("regeneration receipt does not bind the released candidate panel")

    boundary = protocol.get("outcome_boundary")
    if not isinstance(boundary, dict) or any(boundary.values()):
        raise MaterialsCliError("decision protocol crosses the sealed outcome boundary")

    ranking = protocol.get("literature_derived_baseline", {}).get("ranking")
    if not isinstance(ranking, list):
        raise MaterialsCliError("decision protocol has no baseline ranking")
    candidate_ids = {candidate["candidate_id"] for candidate in bank["candidates"]}
    if {item.get("candidate_id") for item in ranking} != candidate_ids:
        raise MaterialsCliError("decision protocol ranking does not cover the frozen panel")

    selection = protocol["prospective_environment_selection"]
    regressions = protocol["target_regression_prediction"]
    if training.get("qualification_environment", {}).get("included_in_final_panel") is not False:
        raise MaterialsCliError("training qualification consumes a final candidate")
    if training.get("qualification_grid", {}).get("uses_phonon_target_outcomes") is not False:
        raise MaterialsCliError("training qualification uses a protected phonon outcome")
    if training_result.get("protocol_sha256") != sha256(training_file):
        raise MaterialsCliError("training result does not bind the frozen qualification protocol")
    if any(training_result.get("outcome_boundary", {}).values()):
        raise MaterialsCliError("training qualification crosses the sealed outcome boundary")
    if final_contract.get("inputs", {}).get("starting_checkpoint_targets_sha256") != sha256(
        starting_targets_file
    ):
        raise MaterialsCliError("final training contract does not bind starting target features")
    if final_contract.get("inputs", {}).get("training_qualification_result_sha256") != sha256(
        training_result_file
    ):
        raise MaterialsCliError("final training contract does not bind training qualification")
    if any(final_contract.get("outcome_boundary", {}).values()):
        raise MaterialsCliError("final training contract crosses the sealed outcome boundary")
    if any(target_features.get("outcome_boundary", {}).values()):
        raise MaterialsCliError("target regression features cross the sealed outcome boundary")
    modeling_inputs = modeling_protocol.get("inputs", {})
    if modeling_inputs.get("final_training_contract_sha256") != sha256(final_contract_file):
        raise MaterialsCliError("modeling protocol does not bind the final training contract")
    if modeling_inputs.get("starting_checkpoint_targets_sha256") != sha256(starting_targets_file):
        raise MaterialsCliError("modeling protocol does not bind starting target features")
    if modeling_inputs.get("target_regression_features_sha256") != sha256(target_features_file):
        raise MaterialsCliError("modeling protocol does not bind target regression features")
    if any(modeling_protocol.get("outcome_boundary", {}).values()):
        raise MaterialsCliError("modeling protocol crosses the sealed outcome boundary")
    if authorization.get("aggregate_utility_fit_sha256") != sha256(aggregate_file):
        raise MaterialsCliError("prospective authorization does not bind the aggregate fit")
    if authorization.get("target_regression_fit_sha256") != sha256(regression_file):
        raise MaterialsCliError("prospective authorization does not bind the regression fit")
    if any(authorization.get("outcome_boundary", {}).values()):
        raise MaterialsCliError("prospective authorization crosses the sealed outcome boundary")
    return {
        "schema_version": "anarres.materials-decision-protocol-report.v1",
        "status": protocol["status"],
        "evidence_tier": "frozen_pre_outcome_protocol",
        "candidate_panel": {
            "candidates": len(candidate_ids),
            "development_environments": selection["development_environments"],
            "prospective_environments": selection["prospective_environments"],
            "development_targets": selection["development_targets"],
            "prospective_targets": selection["prospective_targets"],
        },
        "baseline": {
            "name": protocol["literature_derived_baseline"]["name"],
            "purpose": protocol["literature_derived_baseline"]["purpose"],
            "formula": protocol["literature_derived_baseline"]["formula"],
            "ranking": [
                {
                    "rank": item["rank"],
                    "candidate_id": item["candidate_id"],
                    "role": item["role"],
                    "score": item["score"],
                }
                for item in ranking
            ],
        },
        "selection_evaluation": {
            "sequence": selection["sequence"],
            "candidate_predictors": selection["candidate_predictors"],
            "decision_baselines": selection["decision_baselines"],
            "primary_metrics": selection["primary_metrics"],
        },
        "regression_evaluation": {
            "question": regressions["question"],
            "unit": regressions["unit"],
            "primary_endpoint": regressions["primary_endpoint"],
            "secondary_endpoints": regressions["secondary_endpoints"],
            "metrics": regressions["metrics"],
            "negative_controls": regressions["negative_controls"],
        },
        "training_qualification": {
            "protocol_status": training["status"],
            "result_status": training_result["status"],
            "candidate_id": training["qualification_environment"]["candidate_id"],
            "included_in_final_panel": False,
            "learning_rates": training["qualification_grid"]["learning_rates"],
            "selected_learning_rate": training_result["selected_learning_rate"],
            "selected_checkpoint_sha256": training_result["selected_checkpoint_sha256"],
            "uses_phonon_target_outcomes": False,
            "claim_training": training["proposed_claim_training_after_qualification"],
        },
        "final_training_contract": {
            "status": final_contract["status"],
            "development_environments": len(final_contract["environments"]["development"]),
            "prospective_environments": len(final_contract["environments"]["prospective"]),
            "training_seeds": final_contract["randomization"]["training_seeds"],
            "passes": final_contract["environment_budget"]["passes"],
            "starting_target_features": starting_targets["counts"],
        },
        "development_modeling": {
            "status": modeling_protocol["status"],
            "aggregate_predictors": sorted(
                modeling_protocol["aggregate_utility"]["candidate_predictors"]
            ),
            "aggregate_cross_validation": modeling_protocol["aggregate_utility"][
                "cross_validation"
            ],
            "regression_models": sorted(
                modeling_protocol["target_regressions"]["candidate_models"]
            ),
            "regression_cross_validation": modeling_protocol["target_regressions"][
                "primary_cross_validation"
            ],
            "prospective_freeze": modeling_protocol["prospective_freeze"],
            "target_feature_pairs": target_features["counts"]["candidate_target_pairs"],
        },
        "development_results": {
            "aggregate_model": aggregate["selected_model"]["name"],
            "aggregate_cross_validation": aggregate["selected_model"]["cross_validation"],
            "regression_model": regression["selected_model"]["name"],
            "regression_cross_validation": regression["selected_model"]["primary_cross_validation"],
        },
        "prospective_freeze": {
            "status": authorization["status"],
            "decisions": authorization["decisions"],
            "forecast_counts": authorization["forecast_counts"],
        },
        "outcome_boundary": boundary,
        "predictive_evidence_available": False,
        "artifacts": {
            "candidate_panel": f"sha256:{sha256(bank_path)}",
            "decision_protocol": f"sha256:{sha256(protocol_file)}",
            "regeneration_receipt": f"sha256:{sha256(receipt_file)}",
            "training_qualification": f"sha256:{sha256(training_file)}",
            "training_qualification_result": f"sha256:{sha256(training_result_file)}",
            "starting_checkpoint_targets": f"sha256:{sha256(starting_targets_file)}",
            "final_training_contract": f"sha256:{sha256(final_contract_file)}",
            "target_regression_features": f"sha256:{sha256(target_features_file)}",
            "development_modeling_protocol": f"sha256:{sha256(modeling_protocol_file)}",
            "aggregate_utility_fit": f"sha256:{sha256(aggregate_file)}",
            "target_regression_fit": f"sha256:{sha256(regression_file)}",
            "prospective_training_authorization": f"sha256:{sha256(authorization_file)}",
        },
    }


def command_profile(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    exporter = load_exporter(repository)
    outputs = exporter.export_profiles(
        output_dir=args.output_dir,
        candidate_ids=args.candidate_id,
        force=args.force,
    )
    return {
        "status": "exported",
        "candidate_count": len(outputs),
        "outputs": [str(path) for path in outputs],
    }


def command_results(args: argparse.Namespace) -> dict[str, Any]:
    """Report the scored prospective test and its post-test support audit."""

    repository = repository_root(args.repository)
    exporter = load_exporter(repository)
    authorization_file = prospective_authorization_path(repository)
    aggregate_file = aggregate_fit_path(repository)
    regression_file = regression_fit_path(repository)
    outcomes_file = prospective_outcomes_path(repository)
    score_file = prospective_score_path(repository)
    audit_file = post_prospective_audit_path(repository)
    score = exporter.read_object(score_file)
    outcomes = exporter.read_object(outcomes_file)
    audit = exporter.read_object(audit_file)

    expected = score.get("inputs", {})
    required = {
        "prospective_authorization_sha256": sha256(authorization_file),
        "aggregate_utility_fit_sha256": sha256(aggregate_file),
        "target_regression_fit_sha256": sha256(regression_file),
        "prospective_outcomes_sha256": sha256(outcomes_file),
    }
    for key, value in required.items():
        if expected.get(key) != value:
            raise MaterialsCliError(f"prospective score does not bind {key}")
    if not prospective_boundaries_opened(outcomes):
        raise MaterialsCliError("prospective outcomes have not opened both protected boundaries")
    if audit.get("inputs", {}).get("prospective_prediction_score_sha256") != sha256(score_file):
        raise MaterialsCliError("post-prospective audit does not bind the scored test")
    evidence = audit.get("evidence_boundary", {})
    if evidence.get("frozen_forecast_modified") is not False:
        raise MaterialsCliError("post-prospective audit does not preserve the frozen forecast")
    if evidence.get("support_guard_prespecified") is not False:
        raise MaterialsCliError("post-prospective support guard has an invalid evidence label")

    return {
        "schema_version": "anarres.materials-prospective-results.v1",
        "status": score["status"],
        "evidence_tier": "prospective_test_scored",
        "counts": score["counts"],
        "aggregate_utility": score["aggregate_utility"],
        "allocation_baselines": score["allocation_baselines"],
        "target_regressions": score["target_regressions"],
        "observed_boundary": audit["observed_boundary"],
        "post_prospective_diagnostic": {
            "evidence_tier": audit["status"],
            "support_guard_prespecified": False,
            "would_abstain_at_all_budgets": audit["decision_audit"]["would_abstain_at_all_budgets"],
            "error_attribution": audit["error_attribution"],
        },
        "artifacts": {
            "prospective_authorization": f"sha256:{sha256(authorization_file)}",
            "prospective_outcomes": f"sha256:{sha256(outcomes_file)}",
            "prospective_prediction_score": f"sha256:{sha256(score_file)}",
            "post_prospective_audit": f"sha256:{sha256(audit_file)}",
        },
    }


def command_verify(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    exporter = load_exporter(repository)
    bank = exporter.read_object(exporter.DEFAULT_BANK)
    validation = exporter.read_object(exporter.DEFAULT_VALIDATION)
    candidate_ids = sorted(candidate["candidate_id"] for candidate in bank["candidates"])
    with tempfile.TemporaryDirectory(prefix="anarres-materials-verify-") as directory:
        root = Path(directory)
        first = exporter.export_profiles(output_dir=root / "first", candidate_ids=candidate_ids)
        second = exporter.export_profiles(output_dir=root / "second", candidate_ids=candidate_ids)
        stable = [path.read_bytes() for path in first] == [path.read_bytes() for path in second]
        if not stable:
            raise MaterialsCliError("materials profile export is not deterministic")
        observed_ids = []
        for path in first:
            profile = json.loads(path.read_text(encoding="utf-8"))
            observed_ids.append(profile["environment_id"])
            checks = {check["check_id"]: check for check in profile["qualification_checks"]}
            if checks["measurements-complete"]["status"] != "pass":
                raise MaterialsCliError("full measurement status was not preserved")
            if checks["candidate-outcomes-sealed"]["status"] != "pass":
                raise MaterialsCliError("candidate outcome seal did not pass")
            if checks["final-panel-frozen"]["status"] != "pass":
                raise MaterialsCliError("final panel seal did not pass")
        if observed_ids != candidate_ids:
            raise MaterialsCliError("materials profile export omitted or reordered candidates")

    measurement_shards = validation.get("measurement_sha256")
    if not isinstance(measurement_shards, dict) or len(measurement_shards) != 8:
        raise MaterialsCliError("full measurement shard identities were not preserved")
    result = command_results(args)
    return {
        "status": "pass",
        "profiles_checked": len(candidate_ids),
        "deterministic": True,
        "measurement_records": validation["records"],
        "measurement_shards_pinned": len(measurement_shards),
        "candidate_outcomes_sealed": False,
        "profile_outcome_boundary_preserved": True,
        "final_training_panel_frozen": True,
        "prospective_test_status": result["status"],
        "prospective_result_chain_valid": True,
    }


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--json", action="store_true")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="anarres materials",
        description="Inspect and export released MLIP candidate measurements.",
    )
    commands = result.add_subparsers(dest="command", required=True)

    status = commands.add_parser("status", help="Show the released measurement boundary.")
    add_common(status)
    status.set_defaults(handler=command_status)

    profile = commands.add_parser("profile", help="Export MLIP environment profiles.")
    add_common(profile)
    profile.add_argument("--output-dir", type=Path, required=True)
    profile.add_argument("--candidate-id", action="append")
    profile.add_argument("--force", action="store_true")
    profile.set_defaults(handler=command_profile)

    protocol = commands.add_parser(
        "protocol",
        help="Report the frozen pre-outcome environment-selection and regression protocol.",
    )
    add_common(protocol)
    protocol.set_defaults(handler=command_protocol)

    results = commands.add_parser(
        "results",
        help="Report the scored prospective test and post-test support audit.",
    )
    add_common(results)
    results.set_defaults(handler=command_results)

    qualify = commands.add_parser(
        "qualify-source",
        help="Validate a native atomistic candidate bank without running a model.",
    )
    qualify.add_argument("--manifest", type=Path, required=True)
    qualify.add_argument("--json", action="store_true")
    qualify.set_defaults(handler=command_qualify_source)

    verify = commands.add_parser("verify", help="Verify the released profile adapter.")
    add_common(verify)
    verify.set_defaults(handler=command_verify)
    return result


def print_result(value: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2, sort_keys=True))
        return
    for key, item in value.items():
        label = key.replace("_", " ").title()
        rendered = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
        print(f"{label:<32} {rendered}")


def main() -> None:
    raw_arguments = sys.argv[1:]
    if raw_arguments == ["--anarres-adapter-descriptor"]:
        print(json.dumps(adapter_descriptor(), indent=2, sort_keys=True))
        return
    try:
        raw_arguments = consume_adapter_invocation(raw_arguments, expected_name="materials")
        arguments = parser().parse_args(raw_arguments)
        output = arguments.handler(arguments)
        print_result(output, arguments.json)
    except FileExistsError as error:
        path = error.filename or (error.args[0] if error.args else "output")
        print(f"error: output already exists: {path}", file=sys.stderr)
        raise SystemExit(1) from error
    except (MaterialsCliError, NativeSourceError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
