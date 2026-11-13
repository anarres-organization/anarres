#!/usr/bin/env python3
"""Reconstruct a frozen RxnFlow replay bank from qualified probe artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ARTIFACT_TYPE = "anarres.rxnflow-replay-bank.v1"


def logaddexp(left: float, right: float) -> float:
    if left == -math.inf:
        return right
    if right == -math.inf:
        return left
    maximum = max(left, right)
    return maximum + math.log1p(math.exp(min(left, right) - maximum))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                yield json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON on {path}:{line_number}") from error


def synthon_lookup(env: Any) -> dict[str, list[tuple[str, int]]]:
    result: dict[str, list[tuple[str, int]]] = {}
    for library_name, library in env.synthons.items():
        for index, synthon_id in enumerate(library.synthon_ids):
            result.setdefault(synthon_id, []).append((library_name, index))
    return result


def action_from_export(
    env: Any,
    state: Any,
    exported: dict[str, Any],
    lookup: dict[str, list[tuple[str, int]]],
) -> Any:
    from rxnflow.core.types import Action, ActionType

    try:
        action_type = ActionType[exported["action_type"]]
    except (KeyError, TypeError) as error:
        raise ValueError("exported action has an invalid action_type") from error
    synthon_id = exported.get("synthon_id")
    if synthon_id is None and not action_type.is_unirxn:
        raise ValueError("synthon action is missing synthon_id")
    reaction = exported.get("reaction")
    candidates: list[Any] = []
    if synthon_id is None:
        candidates.append(Action(action_type=action_type, reaction=reaction))
    else:
        if synthon_id not in lookup:
            raise ValueError(f"unknown synthon identifier: {synthon_id}")
        available = {
            (subspace.name, subspace.action_type) for subspace in env.get_action_space(state)
        }
        for library_name, synthon_index in lookup[synthon_id]:
            name = (
                "first_synthon" if action_type.is_first else reaction,
                library_name,
            )
            if (name, action_type) in available:
                candidates.append(
                    Action(
                        action_type=action_type,
                        reaction=reaction,
                        library_name=library_name,
                        synthon_index=synthon_index,
                    )
                )
    if len(candidates) != 1:
        raise ValueError(f"exported action resolves to {len(candidates)} available actions")
    return candidates[0]


def backward_log_probability(
    action: Any,
    routes: list[list[tuple[Any, str]]],
    parent_smiles: str,
    synthon_penalty: float,
) -> float:
    if synthon_penalty <= 0:
        raise ValueError("backward synthon penalty must be positive")
    log_penalty = math.log(synthon_penalty)
    numerator = denominator = -math.inf
    for route in routes:
        num_synthons = sum(not edge.action_type.is_unirxn for edge, _ in route)
        log_weight = -(num_synthons - 1) * log_penalty
        denominator = logaddexp(denominator, log_weight)
        if route and route[0] == (action, parent_smiles):
            numerator = logaddexp(numerator, log_weight)
    if numerator == -math.inf or denominator == -math.inf:
        raise ValueError("backward analysis lost the generated route")
    return numerator - denominator


def reconstruct_trajectory(
    env: Any,
    sample: dict[str, Any],
    record: dict[str, Any],
    *,
    synthon_penalty: float,
    reward_floor: float,
    property_penalty_ratio: float,
) -> Any:
    from rxnflow.core.types import Trajectory, Transition
    from rxnflow.gflownet.property_penalty import compute_property_rewards

    lookup = synthon_lookup(env)
    state = env.initial_state()
    known_routes: list[list[tuple[Any, str]]] = [[]]
    transitions = []
    exported_steps = sample.get("traj")
    if not isinstance(exported_steps, list) or not exported_steps:
        raise ValueError("sample has no exported trajectory")
    for exported in exported_steps:
        action = action_from_export(env, state, exported, lookup)
        parent = state
        next_state = env.step(parent, action)
        if next_state.smiles != exported.get("product_smiles"):
            raise ValueError("replayed product differs from the exported product")
        seeded_routes = [
            [(action, parent.smiles), *route]
            for route in known_routes
            if len(route) <= env.max_reactions
        ]
        known_routes = env.retro_analyzer.run(
            next_state.smiles,
            env.max_reactions,
            seeded_routes,
            max_synthons=env.max_synthons,
        )
        log_p_b = backward_log_probability(action, known_routes, parent.smiles, synthon_penalty)
        transitions.append(Transition(parent, action, next_state.smiles, log_p_b))
        state = next_state

    if not state.terminated:
        raise ValueError("reconstructed trajectory does not terminate")
    final_smiles = sample.get("smiles")
    if state.smiles != final_smiles:
        raise ValueError("reconstructed terminal product differs from sample")
    if record.get("canonical_smiles") != final_smiles:
        raise ValueError("measurement record and sample identify different products")
    if int(record.get("generated_action_count", -1)) != len(transitions):
        raise ValueError("measurement action count differs from reconstructed route")

    target_reward = float(record["target_reward"])
    if not math.isfinite(target_reward) or target_reward < 0:
        raise ValueError("target reward must be finite and nonnegative")
    property_rewards, violations = compute_property_rewards(
        [final_smiles],
        env.property_limits,
        env.max_atoms,
        property_penalty_ratio,
    )
    property_reward = float(property_rewards[0])
    reward = max(target_reward, reward_floor) * max(property_reward, reward_floor)
    metadata = sample.get("metadata", {})
    beta = float(metadata["beta"])
    preference = [float(value) for value in metadata["preference"]]
    condition = {
        key.removeprefix("cond_"): value
        for key, value in metadata.items()
        if key.startswith("cond_")
    }
    return Trajectory(
        steps=transitions,
        final_smiles=final_smiles,
        beta=beta,
        preference=preference,
        objective_rewards=[target_reward],
        property_reward=property_reward,
        property_violation=bool(violations[0]),
        reward=reward,
        valid=True,
        invalid_reason=None,
        cond=condition or None,
    )


def load_memberships(qualification: Path, bank: str) -> tuple[list[str], dict[str, Any]]:
    payload = json.loads(qualification.read_text())
    if payload.get("qualification") != "pass":
        raise ValueError("bank qualification did not pass")
    memberships = payload.get("construction_memberships", {})
    if bank in memberships:
        record_ids = list(memberships[bank])
        expected_size = payload.get("bank_size")
    elif bank in payload.get("banks", {}):
        if payload.get("outcomes_opened") is not False:
            raise ValueError("prospective bank outcomes must remain unopened")
        record_ids = list(payload["banks"][bank].get("members", []))
        expected_size = len(record_ids)
    else:
        raise ValueError(f"unknown qualified bank: {bank}")
    if len(record_ids) != expected_size or len(set(record_ids)) != len(record_ids):
        raise ValueError("bank membership is incomplete or contains duplicates")
    return record_ids, payload


def materialize(
    *,
    env: Any,
    samples_path: Path,
    records_path: Path,
    qualification_path: Path,
    bank: str,
    synthon_penalty: float,
    reward_floor: float,
    property_penalty_ratio: float,
) -> dict[str, Any]:
    record_ids, qualification = load_memberships(qualification_path, bank)
    records = {record["record_id"]: record for record in read_jsonl(records_path)}
    missing = sorted(set(record_ids) - records.keys())
    if missing:
        raise ValueError(f"bank records are missing: {missing[:3]}")
    samples = list(read_jsonl(samples_path))
    items = []
    for record_id in record_ids:
        record = records[record_id]
        returned_index = int(record["returned_index"])
        if not 0 <= returned_index < len(samples):
            raise ValueError(f"returned_index is out of range for {record_id}")
        trajectory = reconstruct_trajectory(
            env,
            samples[returned_index],
            record,
            synthon_penalty=synthon_penalty,
            reward_floor=reward_floor,
            property_penalty_ratio=property_penalty_ratio,
        )
        item = trajectory.to_dict()
        item["anarres_record_id"] = record_id
        items.append(item)
    record_ids_sha256 = canonical_json_sha256(record_ids)
    record_ids_line_sha256 = hashlib.sha256(("\n".join(record_ids) + "\n").encode()).hexdigest()
    return {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": "1.0",
        "study": qualification["study"],
        "bank": bank,
        "item_count": len(items),
        "source": {
            "samples_sha256": sha256_file(samples_path),
            "records_sha256": sha256_file(records_path),
            "qualification_sha256": sha256_file(qualification_path),
            "record_ids_sha256": record_ids_sha256,
            "record_ids_line_sha256": record_ids_line_sha256,
        },
        "training_contract": {
            "backward_synthon_penalty": synthon_penalty,
            "reward_floor": reward_floor,
            "property_penalty_ratio": property_penalty_ratio,
            "online_replay_insertion_required": 0,
        },
        "items_sha256": canonical_json_sha256(items),
        "items": items,
    }


def load_into_fresh_replay(trainer: Any, artifact: dict[str, Any]) -> None:
    if artifact.get("artifact_type") != ARTIFACT_TYPE:
        raise ValueError("unsupported replay-bank artifact")
    if trainer.step != 0 or len(trainer.replay) != 0:
        raise ValueError("replay bank requires a fresh step-zero trainer")
    if trainer.config.training.num_replay_insert != 0:
        raise ValueError("online replay insertion must be disabled")
    items = artifact.get("items", [])
    if len(items) != artifact.get("item_count"):
        raise ValueError("replay-bank item count is inconsistent")
    if canonical_json_sha256(items) != artifact.get("items_sha256"):
        raise ValueError("replay-bank item digest is inconsistent")
    if len(items) > trainer.replay.capacity:
        raise ValueError("replay bank exceeds trainer capacity")
    replay_items = []
    for item in items:
        item = dict(item)
        item.pop("anarres_record_id", None)
        replay_items.append(item)
    trainer.replay.load_state_dict({"capacity": trainer.replay.capacity, "items": replay_items})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-dir", type=Path, required=True)
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--bank", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-atoms", type=int, default=50)
    parser.add_argument("--max-reactions", type=int, default=3)
    parser.add_argument("--min-synthons", type=int, default=2)
    parser.add_argument("--max-synthons", type=int, default=3)
    parser.add_argument("--min-reactions", type=int, default=1)
    parser.add_argument("--mw-limit", type=float, default=500.0)
    parser.add_argument("--backward-synthon-penalty", type=float, default=100.0)
    parser.add_argument("--reward-floor", type=float, default=1e-5)
    parser.add_argument("--property-penalty-ratio", type=float, default=0.2)
    return parser


def main() -> None:
    from rxnflow.envs.env import SynthesisEnv

    args = build_parser().parse_args()
    env = SynthesisEnv(
        args.env_dir,
        args.max_atoms,
        args.max_reactions,
        args.min_synthons,
        args.max_synthons,
        args.min_reactions,
        {"mw": args.mw_limit},
        0,
    )
    try:
        artifact = materialize(
            env=env,
            samples_path=args.samples,
            records_path=args.records,
            qualification_path=args.qualification,
            bank=args.bank,
            synthon_penalty=args.backward_synthon_penalty,
            reward_floor=args.reward_floor,
            property_penalty_ratio=args.property_penalty_ratio,
        )
    finally:
        env.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    temporary.replace(args.output)
    print(
        f"wrote {artifact['item_count']} replay trajectories for {artifact['bank']} "
        f"to {args.output}"
    )


if __name__ == "__main__":
    main()
