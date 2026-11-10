"""Task-oriented CLI for the released Anarres finance workflows."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any


class FinanceCliError(ValueError):
    """Raised when a finance workflow cannot run from released evidence."""


def adapter_descriptor() -> dict[str, Any]:
    """Describe the installed adapter without opening study artifacts."""

    return {
        "schema_version": "anarres.adapter-descriptor.v1",
        "name": "finance",
        "version": "0.1.0",
        "protocol_version": 1,
        "domain": "agentic-finance",
        "executable": "anarres-finance",
        "profile_schema_versions": ["anarres.environment-profile-input.v1"],
        "capabilities": [
            "audit-sources",
            "decide",
            "profile",
            "qualify-policy",
            "reproduce",
            "score-holdout",
            "status",
            "verify",
        ],
        "measurement_contracts": [
            "finance.business-bench-starting-policy-qualification.v1",
        ],
    }


def repository_root(explicit: Path | None = None) -> Path:
    starts = [explicit.resolve()] if explicit is not None else [Path.cwd().resolve()]
    for start in starts:
        for candidate in (start, *start.parents):
            if (candidate / "experiments/finance/README.md").is_file():
                return candidate
    raise FinanceCliError(
        "Anarres repository not found. Run inside the repository or pass --repository"
    )


def load_module(path: Path, name: str) -> ModuleType:
    if not path.is_file():
        raise FinanceCliError(f"required finance implementation is missing: {path}")
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise FinanceCliError(f"cannot load finance implementation: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def read_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FinanceCliError(f"required finance record is missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise FinanceCliError(f"expected a JSON object in {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(root: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = read_object(manifest_path)
    checked = []
    for relative, expected in sorted(manifest.items()):
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise FinanceCliError(f"invalid manifest entry in {manifest_path}")
        path = root / relative
        if not path.is_file():
            raise FinanceCliError(f"manifest artifact is missing: {path}")
        actual = sha256(path)
        if actual != expected:
            raise FinanceCliError(
                f"manifest digest mismatch for {relative}: expected {expected}, found {actual}"
            )
        checked.append(relative)
    return {"manifest": str(manifest_path.relative_to(root)), "artifacts": checked}


def write_json(path: Path, value: dict[str, Any], force: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        raise FileExistsError(path)
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if force:
            os.replace(temporary, path)
        else:
            try:
                os.link(temporary, path)
            except FileExistsError:
                raise FileExistsError(path) from None
            temporary.unlink()
    finally:
        temporary.unlink(missing_ok=True)


def print_result(value: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2, sort_keys=True))
        return
    for key, item in value.items():
        label = key.replace("_", " ").title()
        rendered = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
        print(f"{label:<34} {rendered}")


def finance_root(repository: Path) -> Path:
    return repository / "experiments/finance"


def command_status(args: argparse.Namespace) -> dict[str, Any]:
    root = finance_root(repository_root(args.repository))
    qualification = read_object(root / "environment-selection/QWEN3_8B_QUALIFICATION.json")
    strict = read_object(root / "retrospective-post-training/strict-task-level/SCORE.json")
    strict_rule = strict["evaluations"]["leave_one_source_out"]["practical_rule"]
    selective = read_object(
        root / "retrospective-post-training/strict-task-level/SELECTIVE_SCORE.json"
    )
    selective_rule = selective["rules"]["practical_rule"]["operating_points"]["target_0.85"]
    deployment = selective["rules"]["practical_rule"]["conservative_deployment_point"]
    regression = read_object(
        root / "retrospective-post-training/results/regression_risk_summary.json"
    )
    regression_rule = regression["rules"]["practical_rule"]
    finacumen = read_object(root / "retrospective-post-training/heldout-finacumen/SCORE.json")
    fintoolsyn = read_object(root / "retrospective-post-training/heldout-fintoolsyn/SCORE.json")
    longfinanceqa = read_object(
        root / "retrospective-post-training/heldout-longfinanceqa/SCORE.json"
    )
    holdouts = sorted(
        path.parent.name
        for path in (root / "retrospective-post-training").glob("heldout-*/SCORE.json")
    )
    return {
        "domain": "agentic-finance",
        "capabilities": [
            "source_audit",
            "starting_policy_qualification",
            "environment_profile_export",
            "retrospective_reproduction",
            "frozen_holdout_verification",
            "selective_environment_comparison",
            "candidate_decision",
        ],
        "prospective_environment_outcome_opened": False,
        "evidence_stage": "retrospective_transfer_supported_native_prospective_pending",
        "released_starting_policy": qualification["policy_id"],
        "released_starting_policy_qualified": qualification["qualified"],
        "strict_retrospective_sources": strict["support"]["sources"],
        "strict_retrospective_panels": strict["support"]["panels"],
        "strict_pairwise_ordering": strict_rule["pairwise_ordering"],
        "strict_source_macro_pairwise_ordering": strict_rule["source_macro"]["pairwise_ordering"],
        "strict_source_macro_mean_normalized_regret": strict_rule["source_macro"][
            "mean_normalized_regret"
        ],
        "selective_pairwise_accuracy": selective_rule["selective_pairwise_accuracy"],
        "selective_source_macro_accuracy": selective_rule["source_macro_selective_accuracy"],
        "selective_pairwise_coverage": selective_rule["coverage"],
        "selective_decided_pairs": selective_rule["decided_pairs"],
        "candidate_decision_threshold": deployment["threshold"],
        "candidate_decision_retrospective_accuracy": deployment["pairwise_accuracy"],
        "candidate_decision_retrospective_coverage": deployment["coverage"],
        "regression_risk_contrasts": regression["support"]["contrasts"],
        "regression_risk_source_macro_roc_auc": regression_rule["source_macro_roc_auc"],
        "regression_risk_eligible_sources": regression_rule["eligible_sources"],
        "excluded_source_finacumen_pairwise_correct": finacumen["pairwise_correct"],
        "excluded_source_finacumen_pairwise_scored": finacumen["pairwise_scored"],
        "excluded_source_finacumen_pairwise_abstained": finacumen["pairwise_abstained"],
        "excluded_source_fintoolsyn_directional_correct": fintoolsyn["directional_correct"],
        "excluded_source_fintoolsyn_directional_scored": fintoolsyn["directional_scored"],
        "excluded_source_fintoolsyn_regression_correct": fintoolsyn["regression_correct"],
        "excluded_source_fintoolsyn_regression_scored": fintoolsyn["regression_scored"],
        "outcome_separated_longfinanceqa_directional_correct": longfinanceqa[
            "directional_correct"
        ],
        "outcome_separated_longfinanceqa_directional_scored": longfinanceqa[
            "directional_scored"
        ],
        "outcome_separated_longfinanceqa_families_supported": longfinanceqa[
            "prediction_families_supported"
        ],
        "outcome_separated_longfinanceqa_families_scored": longfinanceqa[
            "prediction_families_scored"
        ],
        "released_holdouts": holdouts,
    }


def command_audit_sources(args: argparse.Namespace) -> dict[str, Any]:
    root = finance_root(repository_root(args.repository)) / "environment-selection"
    module = load_module(root / "scripts/audit_sources.py", "finance_source_audit")
    sources = read_object(root / "SOURCES.json")
    preflight = read_object(root / "PREFLIGHT.json")
    module.validate_sources(sources)
    module.validate_preflight(preflight, sources)
    return {
        "status": "pass",
        "sources": len(sources["sources"]),
        "preflight_source": preflight["source_id"],
        "generator_trials_passed": preflight["passed_trials"],
        "generator_trials_total": preflight["workflow_seed_trials"],
        "scientific_outcomes_opened": preflight["scientific_outcomes_opened"],
    }


def command_decide(args: argparse.Namespace) -> dict[str, Any]:
    """Rank a measured finance candidate panel with calibrated abstention."""

    repository = repository_root(args.repository)
    root = finance_root(repository) / "retrospective-post-training"
    bridge = read_object(root / "results/expanded_summary.json")
    selective = read_object(root / "strict-task-level/SELECTIVE_SCORE.json")
    weights = bridge["practical_rule_weights"]
    calibration = selective["rules"]["practical_rule"]["conservative_deployment_point"]
    threshold = calibration["threshold"]
    panel = read_object(args.input)
    if panel.get("schema_version") != "anarres.finance-candidate-panel.v1":
        raise FinanceCliError("unsupported finance candidate-panel schema")
    unexpected_panel_fields = sorted(
        set(panel) - {"schema_version", "target_id", "baseline_id", "candidates"}
    )
    if unexpected_panel_fields:
        raise FinanceCliError(f"candidate panel has unsupported fields: {unexpected_panel_fields}")
    target_id = panel.get("target_id")
    if not isinstance(target_id, str) or not target_id:
        raise FinanceCliError("candidate panel requires a non-empty target_id")
    candidates = panel.get("candidates")
    if not isinstance(candidates, list) or len(candidates) < 2:
        raise FinanceCliError("candidate panel must contain at least two candidates")

    scores: dict[str, float] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict) or not isinstance(candidate.get("candidate_id"), str):
            raise FinanceCliError("every candidate requires a string candidate_id")
        unexpected_candidate_fields = sorted(set(candidate) - {"candidate_id", "features"})
        if unexpected_candidate_fields:
            raise FinanceCliError(
                f"candidate has unsupported fields: {unexpected_candidate_fields}"
            )
        candidate_id = candidate["candidate_id"]
        if not candidate_id or candidate_id in scores:
            raise FinanceCliError("candidate_id values must be non-empty and unique")
        features = candidate.get("features")
        if not isinstance(features, dict):
            raise FinanceCliError(f"candidate {candidate_id} requires a features object")
        missing = sorted(set(weights) - set(features))
        if missing:
            raise FinanceCliError(f"candidate {candidate_id} is missing features: {missing}")
        unexpected = sorted(set(features) - set(weights))
        if unexpected:
            raise FinanceCliError(
                f"candidate {candidate_id} has unsupported features: {unexpected}"
            )
        for name in weights:
            value = features[name]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise FinanceCliError(f"candidate {candidate_id} feature {name} is not numeric")
            if not 0 <= value <= 1:
                raise FinanceCliError(f"candidate {candidate_id} feature {name} is outside [0, 1]")
        scores[candidate_id] = round(sum(weights[name] * features[name] for name in weights), 9)

    ordered = sorted(scores, key=lambda candidate_id: (-scores[candidate_id], candidate_id))
    leader = ordered[0]
    candidate_set = [
        candidate_id
        for candidate_id in ordered
        if scores[leader] - scores[candidate_id] < threshold
    ]
    pairwise = []
    for index, left in enumerate(sorted(scores)):
        for right in sorted(scores)[index + 1 :]:
            margin = scores[left] - scores[right]
            pairwise.append(
                {
                    "left": left,
                    "right": right,
                    "margin": round(margin, 9),
                    "decision": (
                        "abstain" if abs(margin) < threshold else left if margin > 0 else right
                    ),
                }
            )

    baseline_id = panel.get("baseline_id")
    regressions = []
    if baseline_id is not None:
        if not isinstance(baseline_id, str) or not baseline_id:
            raise FinanceCliError("baseline_id must be a non-empty string")
        if baseline_id not in scores:
            raise FinanceCliError("baseline_id is absent from the candidate panel")
        for candidate_id in ordered:
            if candidate_id == baseline_id:
                continue
            margin = scores[candidate_id] - scores[baseline_id]
            regressions.append(
                {
                    "candidate_id": candidate_id,
                    "baseline_id": baseline_id,
                    "margin": round(margin, 9),
                    "direction": (
                        "improve"
                        if margin >= threshold
                        else "regress"
                        if margin <= -threshold
                        else "abstain"
                    ),
                }
            )

    result = {
        "schema_version": "anarres.finance-candidate-decision.v1",
        "target_id": target_id,
        "decision": "select" if len(candidate_set) == 1 else "abstain",
        "selected_candidate": leader if len(candidate_set) == 1 else None,
        "candidate_set": candidate_set,
        "threshold": threshold,
        "candidate_scores": [
            {"candidate_id": candidate_id, "score": scores[candidate_id]}
            for candidate_id in ordered
        ],
        "pairwise_decisions": pairwise,
        "regression_directions": regressions,
        "evidence": {
            "status": "retrospective_calibration_requires_prospective_validation",
            "pairwise_accuracy": calibration["pairwise_accuracy"],
            "coverage": calibration["coverage"],
            "sources_with_decisions": calibration["sources_with_decisions"],
        },
    }
    if args.output is not None:
        write_json(args.output, result, force=args.force)
    return result


def command_qualify_policy(args: argparse.Namespace) -> dict[str, Any]:
    root = finance_root(repository_root(args.repository)) / "environment-selection"
    module = load_module(
        root / "scripts/score_policy_qualification.py", "finance_policy_qualification"
    )
    rows = module.read_rows(args.input)
    summary = module.score(
        rows,
        expected_workflows=args.expected_workflows,
        expected_scenarios_per_workflow=args.expected_scenarios_per_workflow,
        group_size=args.group_size,
    )
    if args.output is not None:
        write_json(args.output, summary, force=args.force)
    return summary


def command_profile(args: argparse.Namespace) -> dict[str, Any]:
    root = finance_root(repository_root(args.repository)) / "environment-selection"
    module = load_module(root / "export_environment_profile.py", "finance_profile_export")
    output = module.export_profile(
        result_path=args.result or module.DEFAULT_RESULT,
        protocol_path=args.protocol or module.DEFAULT_PROTOCOL,
        preflight_path=args.preflight or module.DEFAULT_PREFLIGHT,
        sources_path=args.sources or module.DEFAULT_SOURCES,
        harness_path=args.harness or module.DEFAULT_HARNESS,
        output_dir=args.output_dir,
        force=args.force,
    )
    profile = read_object(output)
    return {
        "status": "exported",
        "output": str(output),
        "sha256": f"sha256:{sha256(output)}",
        "environment_id": profile["environment_id"],
        "qualified": profile["attributes"]["qualified"],
        "coordinates": len(profile["coordinates"]),
    }


def finance_test_paths(root: Path) -> list[Path]:
    return sorted(root.rglob("test_*.py"))


def run_finance_tests(root: Path) -> dict[str, Any]:
    records = []
    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = "0"
    for test in finance_test_paths(root):
        relative = test.relative_to(root)
        completed = subprocess.run(
            [sys.executable, str(relative)],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )
        records.append(
            {
                "test": str(relative),
                "passed": completed.returncode == 0,
                "returncode": completed.returncode,
            }
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise FinanceCliError(f"finance test failed: {relative}\n{detail}")
    return {"status": "pass", "tests": records, "test_count": len(records)}


def claim_artifacts(root: Path) -> list[Path]:
    retrospective = root / "retrospective-post-training"
    paths = list((retrospective / "results").glob("*.json"))
    paths.extend((retrospective / "figures").glob("*.svg"))
    paths.extend((retrospective / "strict-task-level").glob("*.json"))
    for holdout in retrospective.glob("heldout-*"):
        paths.extend(holdout.glob("SCORE.json"))
        paths.extend(holdout.glob("MANIFEST*.json"))
    return sorted(set(paths))


def isolated_reproduction(
    repository: Path,
) -> tuple[dict[str, Any], Path, tempfile.TemporaryDirectory]:
    temporary = tempfile.TemporaryDirectory(prefix="anarres-finance-reproduction-")
    copied = Path(temporary.name) / "finance"
    shutil.copytree(finance_root(repository), copied)
    report = run_finance_tests(copied)
    artifacts = {}
    original = finance_root(repository)
    for path in claim_artifacts(copied):
        relative = path.relative_to(copied)
        original_path = original / relative
        if not original_path.is_file():
            raise FinanceCliError(f"released claim artifact is missing: {relative}")
        regenerated_digest = sha256(path)
        released_digest = sha256(original_path)
        if regenerated_digest != released_digest:
            raise FinanceCliError(
                "regenerated claim artifact differs from the release: "
                f"{relative} (released {released_digest}, regenerated {regenerated_digest})"
            )
        artifacts[str(relative)] = f"sha256:{regenerated_digest}"
    report["artifacts"] = artifacts
    return report, copied, temporary


def exhaustive_verification(repository: Path) -> dict[str, Any]:
    """Run every released finance test in an isolated evidence copy."""

    report, _, temporary = isolated_reproduction(repository)
    temporary.cleanup()
    report["mode"] = "exhaustive"
    return report


def compact_verification(repository: Path) -> dict[str, Any]:
    """Validate released finance evidence without regenerating every artifact."""

    root = finance_root(repository)
    manifest = verify_manifest(root, root / "COMPACT_VERIFICATION_MANIFEST.sha256.json")
    source_audit = command_audit_sources(type("Args", (), {"repository": repository})())

    qualification = read_object(root / "environment-selection/QWEN3_8B_QUALIFICATION.json")
    if qualification.get("status") != "qualification_complete":
        raise FinanceCliError("starting-policy qualification is not complete")
    if qualification.get("qualified") is not False:
        raise FinanceCliError("released Qwen3-8B qualification must preserve its failed gate")

    retrospective = root / "retrospective-post-training"
    summary = read_object(retrospective / "results/summary.json")
    expanded = read_object(retrospective / "results/expanded_summary_corrected.json")
    strict = read_object(retrospective / "strict-task-level/SCORE.json")
    selective = read_object(retrospective / "strict-task-level/SELECTIVE_SCORE.json")
    regression = read_object(retrospective / "results/regression_risk_summary.json")
    fintoolsyn = read_object(retrospective / "heldout-fintoolsyn/SCORE.json")
    longfinanceqa = read_object(retrospective / "heldout-longfinanceqa/SCORE.json")
    if summary.get("status") != "retrospective_exploratory":
        raise FinanceCliError("compact retrospective summary has an unexpected status")
    if expanded.get("support", {}).get("sources") != 16:
        raise FinanceCliError("expanded retrospective support no longer contains 16 sources")
    if strict.get("support", {}).get("panels") != 79:
        raise FinanceCliError("strict task-level support no longer contains 79 panels")
    selective_rule = (
        selective.get("rules", {})
        .get("practical_rule", {})
        .get("operating_points", {})
        .get("target_0.85", {})
    )
    if selective_rule.get("selective_pairwise_accuracy") != 0.904255:
        raise FinanceCliError("selective audit no longer matches the released accuracy")
    if selective_rule.get("coverage") != 0.760518:
        raise FinanceCliError("selective audit no longer matches the released coverage")
    if regression.get("support", {}).get("contrasts") != 165:
        raise FinanceCliError("regression-risk audit no longer contains 165 contrasts")
    if (
        regression.get("rules", {}).get("practical_rule", {}).get("source_macro_roc_auc")
        != 0.815183
    ):
        raise FinanceCliError("regression-risk audit no longer matches the released score")
    if (fintoolsyn.get("directional_correct"), fintoolsyn.get("directional_scored")) != (9, 9):
        raise FinanceCliError("FinToolSyn holdout no longer matches the released score")
    if (fintoolsyn.get("regression_correct"), fintoolsyn.get("regression_scored")) != (3, 3):
        raise FinanceCliError("FinToolSyn regression audit no longer matches the release")
    if (
        longfinanceqa.get("directional_correct"),
        longfinanceqa.get("directional_scored"),
    ) != (24, 25):
        raise FinanceCliError("LongFinanceQA component test no longer matches the release")
    if (
        longfinanceqa.get("prediction_families_supported"),
        longfinanceqa.get("prediction_families_scored"),
    ) != (4, 4):
        raise FinanceCliError("LongFinanceQA family score no longer matches the release")

    holdouts = []
    for directory in sorted(retrospective.glob("heldout-*")):
        score = read_object(directory / "SCORE.json")
        identity_files = [
            name
            for name in ("SOURCE.json", "FREEZE.json", "CONTRACT.json", "PREDICTIONS.json")
            if (directory / name).is_file()
        ]
        if not identity_files:
            raise FinanceCliError(f"frozen holdout has no identity record: {directory.name}")
        if not isinstance(score.get("status"), str) or not score["status"]:
            raise FinanceCliError(f"frozen holdout has no score status: {directory.name}")
        holdouts.append(
            {
                "holdout": directory.name,
                "identity_files": identity_files,
                "score_status": score["status"],
            }
        )

    return {
        "status": "pass",
        "mode": "compact",
        "manifest_artifacts": len(manifest["artifacts"]),
        "source_pins": source_audit["sources"],
        "starting_policy": qualification["policy_id"],
        "starting_policy_qualified": qualification["qualified"],
        "retrospective_sources": expanded["support"]["sources"],
        "strict_panels": strict["support"]["panels"],
        "selective_pairwise_accuracy": selective_rule["selective_pairwise_accuracy"],
        "selective_pairwise_coverage": selective_rule["coverage"],
        "regression_risk_source_macro_roc_auc": regression["rules"]["practical_rule"][
            "source_macro_roc_auc"
        ],
        "fintoolsyn_directional_correct": fintoolsyn["directional_correct"],
        "fintoolsyn_directional_scored": fintoolsyn["directional_scored"],
        "fintoolsyn_regression_correct": fintoolsyn["regression_correct"],
        "fintoolsyn_regression_scored": fintoolsyn["regression_scored"],
        "longfinanceqa_directional_correct": longfinanceqa["directional_correct"],
        "longfinanceqa_directional_scored": longfinanceqa["directional_scored"],
        "longfinanceqa_families_supported": longfinanceqa["prediction_families_supported"],
        "longfinanceqa_families_scored": longfinanceqa["prediction_families_scored"],
        "holdouts": holdouts,
    }


def command_verify(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    if getattr(args, "exhaustive", False):
        return exhaustive_verification(repository)
    return compact_verification(repository)


def command_score_holdout(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    temporary = tempfile.TemporaryDirectory(prefix="anarres-finance-holdout-")
    copied = Path(temporary.name) / "finance"
    shutil.copytree(finance_root(repository), copied)
    name = args.name if args.name.startswith("heldout-") else f"heldout-{args.name}"
    holdout = copied / "retrospective-post-training" / name
    try:
        if not holdout.is_dir():
            raise FinanceCliError(f"unknown finance holdout: {args.name}")
        tests = [
            path
            for path in (holdout / "test_freeze.py", holdout / "test_score.py")
            if path.is_file()
        ]
        if not tests:
            raise FinanceCliError(f"finance holdout has no released scoring test: {args.name}")
        for test in tests:
            environment = os.environ.copy()
            environment["PYTHONHASHSEED"] = "0"
            completed = subprocess.run(
                [sys.executable, test.name],
                cwd=holdout,
                capture_output=True,
                text=True,
                check=False,
                env=environment,
            )
            if completed.returncode != 0:
                detail = completed.stderr.strip() or completed.stdout.strip()
                raise FinanceCliError(f"finance holdout failed: {name}\n{detail}")
        score_path = holdout / "SCORE.json"
        score = read_object(score_path)
        return {
            "status": "pass",
            "holdout": name,
            "tests": [path.name for path in tests],
            "score_sha256": f"sha256:{sha256(score_path)}",
            "score": score,
        }
    finally:
        temporary.cleanup()


def copy_reproduced_artifacts(
    copied: Path, output: Path, report: dict[str, Any], force: bool
) -> None:
    artifacts = claim_artifacts(copied)
    destinations = [output / path.relative_to(copied) for path in artifacts]
    report_path = output / "REPRODUCTION.json"
    if not force:
        existing = [path for path in (*destinations, report_path) if path.exists()]
        if existing:
            raise FileExistsError(existing[0])
    for source, destination in zip(artifacts, destinations, strict=True):
        destination.parent.mkdir(parents=True, exist_ok=True)
        if force:
            shutil.copy2(source, destination)
            continue
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", dir=destination.parent
        )
        os.close(descriptor)
        temporary_path = Path(temporary_name)
        try:
            shutil.copy2(source, temporary_path)
            os.link(temporary_path, destination)
        finally:
            temporary_path.unlink(missing_ok=True)
    write_json(report_path, report, force=force)


def command_reproduce(args: argparse.Namespace) -> dict[str, Any]:
    report, copied, temporary = isolated_reproduction(repository_root(args.repository))
    try:
        copy_reproduced_artifacts(copied, args.output_dir, report, args.force)
    finally:
        temporary.cleanup()
    return {
        "status": "reproduced",
        "test_count": report["test_count"],
        "artifact_count": len(report["artifacts"]),
        "output": str(args.output_dir),
    }


def add_common(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument("--repository", type=Path)
    subparser.add_argument("--json", action="store_true")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="anarres finance",
        description="Audit, qualify, reproduce, and export released agentic-finance evidence.",
    )
    commands = result.add_subparsers(dest="command", required=True)

    status = commands.add_parser("status", help="Show released finance capabilities and stage.")
    add_common(status)
    status.set_defaults(handler=command_status)

    sources = commands.add_parser("audit-sources", help="Validate source pins and preflight.")
    add_common(sources)
    sources.set_defaults(handler=command_audit_sources)

    decide = commands.add_parser(
        "decide", help="Rank a measured finance candidate panel or abstain."
    )
    add_common(decide)
    decide.add_argument("input", type=Path)
    decide.add_argument("--output", type=Path)
    decide.add_argument("--force", action="store_true")
    decide.set_defaults(handler=command_decide)

    qualify = commands.add_parser("qualify-policy", help="Score one native policy-attempt record.")
    add_common(qualify)
    qualify.add_argument("input", type=Path)
    qualify.add_argument("--expected-workflows", type=int, default=4)
    qualify.add_argument("--expected-scenarios-per-workflow", type=int, default=8)
    qualify.add_argument("--group-size", type=int, default=4)
    qualify.add_argument("--output", type=Path)
    qualify.add_argument("--force", action="store_true")
    qualify.set_defaults(handler=command_qualify_policy)

    profile = commands.add_parser("profile", help="Export a native qualification profile input.")
    add_common(profile)
    profile.add_argument("--result", type=Path)
    profile.add_argument("--protocol", type=Path)
    profile.add_argument("--preflight", type=Path)
    profile.add_argument("--sources", type=Path)
    profile.add_argument("--harness", type=Path)
    profile.add_argument("--output-dir", type=Path, required=True)
    profile.add_argument("--force", action="store_true")
    profile.set_defaults(handler=command_profile)

    verify = commands.add_parser("verify", help="Validate released finance evidence.")
    add_common(verify)
    verify.add_argument(
        "--exhaustive",
        action="store_true",
        help="copy the study and re-run every released finance test",
    )
    verify.set_defaults(handler=command_verify)

    holdout = commands.add_parser("score-holdout", help="Re-score one frozen finance holdout.")
    add_common(holdout)
    holdout.add_argument("name")
    holdout.set_defaults(handler=command_score_holdout)

    reproduce = commands.add_parser(
        "reproduce", help="Regenerate claim artifacts in an isolated copy."
    )
    add_common(reproduce)
    reproduce.add_argument("--output-dir", type=Path, required=True)
    reproduce.add_argument("--force", action="store_true")
    reproduce.set_defaults(handler=command_reproduce)
    return result


def main() -> None:
    if sys.argv[1:] == ["--anarres-adapter-descriptor"]:
        print(json.dumps(adapter_descriptor(), indent=2, sort_keys=True))
        return
    arguments = parser().parse_args()
    try:
        output = arguments.handler(arguments)
        print_result(output, arguments.json)
    except FileExistsError as error:
        path = error.filename or (error.args[0] if error.args else "output")
        print(f"error: output already exists: {path}", file=sys.stderr)
        raise SystemExit(1) from error
    except (FinanceCliError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
