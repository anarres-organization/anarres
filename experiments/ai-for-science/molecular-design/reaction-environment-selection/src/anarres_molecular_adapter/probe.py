"""Plan and execute the released Q07820 endpoint producer from a native source."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .source import _artifact, bundle_digest, load_source, qualify_source, sha256_file


class MolecularProbeError(ValueError):
    """Raised when a source cannot enter the released endpoint producer."""


def _canonical_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _study_root(repository: Path) -> Path:
    root = repository / "experiments/ai-for-science/molecular-design/reaction-environment-selection"
    if not (root / "scripts/sample_endpoint_policy.py").is_file():
        raise MolecularProbeError("repository does not contain the molecular endpoint producer")
    return root


def _required_target_artifact(source_root: Path, target: dict[str, Any], name: str) -> Path:
    assets = target.get("endpoint_assets")
    if not isinstance(assets, dict) or name not in assets:
        raise MolecularProbeError(f"prepared target does not declare endpoint asset: {name}")
    return _artifact(source_root, assets[name], f"endpoint asset {name}")


def build_probe_plan(
    *,
    source_root: Path,
    repository: Path,
    policy_id: str,
    policy_revision: str,
    output: Path,
    sampler_python: Path,
    oracle_python: Path,
    device: str,
    docking_jobs: int,
    metric_jobs: int,
) -> dict[str, Any]:
    """Bind one source and policy to the unchanged PR 36 endpoint stages."""

    qualified = qualify_source(source_root)
    declaration = load_source(source_root)
    policy = declaration["starting_policy"]
    if policy_id != policy["policy_id"] or policy_revision != policy["revision"]:
        raise MolecularProbeError("requested policy identity differs from the qualified source")
    if declaration["target_id"] != "Q07820":
        raise MolecularProbeError("the released endpoint producer currently supports Q07820 only")
    if not sampler_python.is_file() or not oracle_python.is_file():
        raise MolecularProbeError("sampler and oracle interpreters must be existing files")

    study = _study_root(repository.resolve())
    matched_contract = study / "MATCHED_TRAINING_EVALUATION_CONTRACT_V1.json"
    endpoint_contract = study / "STARTING_POLICY_ENDPOINT_QUALIFICATION_CONTRACT_V2.json"
    thresholds = _required_target_artifact(source_root, declaration["target"], "thresholds")
    matched = json.loads(matched_contract.read_text(encoding="utf-8"))
    endpoint = json.loads(endpoint_contract.read_text(encoding="utf-8"))
    probe_contract_path = _artifact(
        source_root, declaration["contracts"]["probe"], "probe contract"
    )
    probe = json.loads(probe_contract_path.read_text(encoding="utf-8"))
    training_seed = probe.get("training_seed")
    checkpoint_step = probe.get("checkpoint_step")
    if checkpoint_step != 0 or probe.get("arm") != "warm_start":
        raise MolecularProbeError("source probing currently requires the frozen warm-start panel")
    if probe.get("matched_contract_sha256") != sha256_file(matched_contract):
        raise MolecularProbeError("probe contract does not bind the released matched contract")
    if probe.get("endpoint_contract_sha256") != sha256_file(endpoint_contract):
        raise MolecularProbeError("probe contract does not bind the released endpoint contract")
    if policy_revision != f"sha256:{matched['starting_policy']['weights_only_sha256']}":
        raise MolecularProbeError("source policy differs from the frozen Q07820 warm start")
    try:
        evaluation_seed = matched["evaluation"]["seeds"][str(training_seed)]["0"]
    except KeyError as error:
        raise MolecularProbeError(
            "probe training seed is absent from the matched contract"
        ) from error
    attempts = matched["evaluation"]["attempts_per_policy_seed_checkpoint"]
    if probe.get("attempts") != attempts or probe.get("seed") != evaluation_seed:
        raise MolecularProbeError("probe attempts or seed differ from the frozen evaluation panel")

    environment = _artifact(
        source_root,
        declaration["reaction_environment"]["prepared_environment"],
        "prepared reaction environment",
        directory=True,
    )
    policy_path = _artifact(source_root, policy, "starting policy")
    prepared_target = _artifact(
        source_root,
        declaration["target"]["prepared_target"],
        "prepared target",
        directory=True,
    )
    protein = _required_target_artifact(source_root, declaration["target"], "protein")
    pocket = _required_target_artifact(source_root, declaration["target"], "pocket")
    reference_actives = _required_target_artifact(
        source_root, declaration["target"], "reference_actives"
    )
    reference_interactions = _required_target_artifact(
        source_root, declaration["target"], "reference_interaction_scores"
    )

    sample_dir = output / "01-sample"
    docking_dir = output / "02-docking"
    metrics_dir = output / "03-metrics"
    score_dir = output / "04-score"
    gate_dir = output / "05-gate"
    contract_id = endpoint["contract"]
    commands = [
        {
            "name": "sample",
            "command": [
                str(sampler_python),
                str(study / "scripts/sample_endpoint_policy.py"),
                "--contract",
                str(matched_contract),
                "--policy",
                str(policy_path),
                "--env-dir",
                str(environment),
                "--arm",
                "warm_start",
                "--training-seed",
                str(training_seed),
                "--checkpoint-step",
                "0",
                "--device",
                device,
                "--batch-size",
                str(probe["batch_size"]),
                "--output",
                str(sample_dir / "samples.jsonl"),
                "--manifest-output",
                str(sample_dir / "SAMPLE_MANIFEST.json"),
            ],
            "outputs": [
                str(sample_dir / "samples.jsonl"),
                str(sample_dir / "SAMPLE_MANIFEST.json"),
            ],
        },
        {
            "name": "dock",
            "command": [
                str(oracle_python),
                str(study / "scripts/dock_endpoint_panel.py"),
                "panel",
                "--samples",
                str(sample_dir / "samples.jsonl"),
                "--prepared-target",
                str(prepared_target),
                "--attempts",
                str(attempts),
                "--sample-seed",
                str(evaluation_seed),
                "--contract",
                contract_id,
                "--seed",
                str(probe.get("docking_seed", 20261108)),
                "--exhaustiveness",
                str(probe.get("exhaustiveness", 8)),
                "--timeout-seconds",
                str(probe.get("timeout_seconds", 300)),
                "--jobs",
                str(docking_jobs),
                "--output-dir",
                str(docking_dir / "artifacts"),
                "--output-records",
                str(docking_dir / "records.jsonl"),
                "--report",
                str(docking_dir / "REPORT.json"),
            ],
            "outputs": [str(docking_dir / "records.jsonl"), str(docking_dir / "REPORT.json")],
        },
        {
            "name": "metrics",
            "command": [
                str(oracle_python),
                str(study / "scripts/score_endpoint_metrics.py"),
                "--docking-records",
                str(docking_dir / "records.jsonl"),
                "--protein",
                str(protein),
                "--pocket",
                str(pocket),
                "--reference-actives",
                str(reference_actives),
                "--reference-interaction-scores",
                str(reference_interactions),
                "--attempts",
                str(attempts),
                "--contract",
                contract_id,
                "--jobs",
                str(metric_jobs),
                "--interaction-jobs",
                str(metric_jobs),
                "--output-records",
                str(metrics_dir / "records.jsonl"),
                "--report",
                str(metrics_dir / "REPORT.json"),
            ],
            "outputs": [str(metrics_dir / "records.jsonl"), str(metrics_dir / "REPORT.json")],
        },
        {
            "name": "score",
            "command": [
                str(oracle_python),
                str(study / "scripts/score_qualifying_hits.py"),
                "--records",
                str(metrics_dir / "records.jsonl"),
                "--thresholds",
                str(thresholds),
                "--output",
                str(score_dir / "SCORE.json"),
            ],
            "outputs": [str(score_dir / "SCORE.json")],
        },
        {
            "name": "gate",
            "command": [
                str(oracle_python),
                str(study / "scripts/apply_starting_policy_endpoint_gate.py"),
                "--score",
                str(score_dir / "SCORE.json"),
                "--contract",
                str(endpoint_contract),
                "--sample",
                str(sample_dir / "samples.jsonl"),
                "--docking-report",
                str(docking_dir / "REPORT.json"),
                "--metrics-report",
                str(metrics_dir / "REPORT.json"),
                "--output",
                str(gate_dir / "RESULT.json"),
            ],
            "outputs": [str(gate_dir / "RESULT.json")],
        },
    ]
    plan = {
        "schema_version": "anarres.molecular-probe-plan.v1",
        "status": "planned",
        "claim_boundary": (
            "This plan binds a qualified source and policy to the released Q07820 endpoint. "
            "No target-training comparison is performed."
        ),
        "source_revision": f"sha256:{bundle_digest(source_root)}",
        "policy_id": policy_id,
        "policy_revision": policy_revision,
        "target_id": qualified["target_id"],
        "attempts": attempts,
        "evaluation_seed": evaluation_seed,
        "runtime": {
            "sampler_python": str(sampler_python),
            "oracle_python": str(oracle_python),
            "device": device,
            "docking_jobs": docking_jobs,
            "metric_jobs": metric_jobs,
        },
        "commands": commands,
        "outcomes_opened": False,
    }
    plan["plan_sha256"] = _canonical_digest(plan)
    return plan


def _verify_stage(stage: dict[str, Any], sentinel: Path) -> dict[str, Any]:
    record = json.loads(sentinel.read_text(encoding="utf-8"))
    if record.get("command_sha256") != _canonical_digest(stage["command"]):
        raise MolecularProbeError(f"completed stage command changed: {stage['name']}")
    expected = record.get("outputs", {})
    for output in stage["outputs"]:
        path = Path(output)
        if not path.is_file() or expected.get(output) != sha256_file(path):
            raise MolecularProbeError(f"completed stage output changed: {output}")
    return record


def execute_probe_plan(
    plan: dict[str, Any], output: Path, *, force_incomplete: bool = False
) -> dict[str, Any]:
    """Execute or resume an immutable plan one stage at a time."""

    completed: list[dict[str, Any]] = []
    for index, stage in enumerate(plan["commands"], start=1):
        stage_dir = output / f"stage-{index:02d}-{stage['name']}"
        sentinel = stage_dir / "STAGE.json"
        if sentinel.is_file():
            completed.append(_verify_stage(stage, sentinel))
            continue
        if force_incomplete:
            if stage_dir.exists():
                shutil.rmtree(stage_dir)
            output_parents = {Path(path).parent for path in stage["outputs"]}
            for parent in output_parents:
                if parent.exists():
                    shutil.rmtree(parent)
        stage_dir.mkdir(parents=True, exist_ok=True)
        log = stage_dir / "execution.log"
        with log.open("w", encoding="utf-8") as handle:
            process = subprocess.run(
                stage["command"],
                stdout=handle,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
        if process.returncode != 0:
            raise MolecularProbeError(
                f"probe stage failed with exit {process.returncode}: {stage['name']}; see {log}"
            )
        outputs = {
            path: sha256_file(Path(path)) for path in stage["outputs"] if Path(path).is_file()
        }
        if set(outputs) != set(stage["outputs"]):
            raise MolecularProbeError(f"probe stage omitted a required output: {stage['name']}")
        record = {
            "stage": stage["name"],
            "status": "complete",
            "command_sha256": _canonical_digest(stage["command"]),
            "outputs": outputs,
            "log_sha256": sha256_file(log),
        }
        sentinel.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        completed.append(record)
    result = {
        "schema_version": "anarres.molecular-probe-run.v1",
        "status": "complete",
        "plan_sha256": plan["plan_sha256"],
        "stages": completed,
        "result": plan["commands"][-1]["outputs"][0],
    }
    path = output / "PROBE_RUN.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result
