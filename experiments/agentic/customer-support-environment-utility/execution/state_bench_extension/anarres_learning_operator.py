"""Deterministic episodic-memory construction and retrieval for STATE-Bench."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
TASK_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
GIT_REVISION_PATTERN = re.compile(r"[0-9a-f]{40}")
OPERATOR_ID = "state_bench_episodic_bm25_v1"
K1 = 1.5
B = 0.75


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def compact_trajectory(path: Path, task_id: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    conversation = payload.get("conversation")
    if not isinstance(conversation, list) or not conversation:
        raise ValueError(f"{path}: conversation is missing")
    user_messages = []
    assistant_messages = []
    tool_names = []
    for turn in conversation:
        if not isinstance(turn, dict):
            raise ValueError(f"{path}: conversation turn must be an object")
        role = turn.get("role")
        content = _text(turn.get("content"))
        if role == "user" and content:
            user_messages.append(content)
        elif role == "assistant":
            if content:
                assistant_messages.append(content)
            calls = turn.get("tool_calls")
            if calls is not None:
                if not isinstance(calls, list):
                    raise ValueError(f"{path}: tool_calls must be a list when present")
                for call in calls:
                    if isinstance(call, dict) and _text(call.get("name")):
                        tool_names.append(_text(call["name"]))
    if not user_messages or not assistant_messages:
        raise ValueError(f"{path}: trajectory lacks a user request or assistant response")
    request_text = " | ".join(user_messages)
    procedure = " -> ".join(tool_names) if tool_names else "no domain tools recorded"
    response_text = " | ".join(assistant_messages)
    learning = (
        f"Prior customer-support interaction. Requests: {request_text}\n"
        f"Tool sequence: {procedure}\n"
        f"Responses: {response_text}"
    )
    return {
        "task_id": task_id,
        "source_trajectory_sha256": sha256(path),
        "retrieval_text": f"{request_text} {procedure}",
        "learning": learning,
    }


def membership_hash(task_ids: list[str]) -> str:
    return hashlib.sha256(("\n".join(sorted(task_ids)) + "\n").encode()).hexdigest()


def build_artifact(
    trajectory_root: Path,
    task_ids: list[str],
    *,
    source_revision: str,
    candidate_plan_sha256: str,
    arm: str,
    expected_membership_sha256: str,
) -> dict:
    ordered_ids = sorted(task_ids)
    if len(ordered_ids) != len(set(ordered_ids)) or not ordered_ids:
        raise ValueError("learning artifact requires unique task identities")
    if any(
        not isinstance(task_id, str) or not TASK_ID_PATTERN.fullmatch(task_id)
        for task_id in ordered_ids
    ):
        raise ValueError("learning artifact contains an invalid task identity")
    actual_membership = membership_hash(ordered_ids)
    if actual_membership != expected_membership_sha256:
        raise ValueError("candidate membership differs from its frozen hash")
    records = []
    for task_id in ordered_ids:
        path = trajectory_root / f"{task_id}.json"
        if not path.is_file():
            raise ValueError(f"released training trajectory is missing: {task_id}")
        records.append(compact_trajectory(path, task_id))
    return {
        "schema_version": 1,
        "operator_id": OPERATOR_ID,
        "source_revision": source_revision,
        "candidate_plan_sha256": candidate_plan_sha256,
        "arm": arm,
        "candidate_membership_sha256": actual_membership,
        "record_count": len(records),
        "records": records,
    }


def validate_artifact(payload: dict) -> None:
    if payload.get("schema_version") != 1 or payload.get("operator_id") != OPERATOR_ID:
        raise ValueError("unsupported learning artifact")
    if not GIT_REVISION_PATTERN.fullmatch(str(payload.get("source_revision", ""))):
        raise ValueError("learning artifact lacks a valid source revision")
    if not SHA256_PATTERN.fullmatch(str(payload.get("candidate_plan_sha256", ""))):
        raise ValueError("learning artifact lacks a valid candidate-plan hash")
    if not isinstance(payload.get("arm"), str) or not payload["arm"].strip():
        raise ValueError("learning artifact lacks a candidate arm")
    if not SHA256_PATTERN.fullmatch(str(payload.get("candidate_membership_sha256", ""))):
        raise ValueError("learning artifact lacks a valid membership hash")
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != payload.get("record_count"):
        raise ValueError("learning artifact record count is inconsistent")
    task_ids = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("learning record must be an object")
        if not all(_text(record.get(name)) for name in ("task_id", "retrieval_text", "learning")):
            raise ValueError("learning record lacks required text")
        if not TASK_ID_PATTERN.fullmatch(_text(record.get("task_id"))):
            raise ValueError("learning record contains an invalid task identity")
        if not SHA256_PATTERN.fullmatch(_text(record.get("source_trajectory_sha256"))):
            raise ValueError("learning record lacks a source trajectory hash")
        task_ids.append(record["task_id"])
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("learning artifact repeats a task identity")
    if membership_hash(task_ids) != payload.get("candidate_membership_sha256"):
        raise ValueError("learning artifact membership hash is inconsistent")


def retrieve(payload: dict, query: str, top_k: int = 3) -> list[str]:
    validate_artifact(payload)
    if not isinstance(query, str) or not query.strip():
        raise ValueError("retrieval query must be non-empty")
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    records = payload["records"]
    documents = [tokenize(record["retrieval_text"]) for record in records]
    query_terms = Counter(tokenize(query))
    average_length = sum(len(document) for document in documents) / len(documents)
    document_frequency = Counter()
    for document in documents:
        document_frequency.update(set(document))
    scored = []
    for record, document in zip(records, documents, strict=True):
        frequencies = Counter(document)
        score = 0.0
        for term, query_count in query_terms.items():
            frequency = frequencies[term]
            if not frequency:
                continue
            inverse_frequency = math.log(
                1.0
                + (len(documents) - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5)
            )
            normalizer = frequency + K1 * (1.0 - B + B * len(document) / max(average_length, 1.0))
            score += query_count * inverse_frequency * frequency * (K1 + 1.0) / normalizer
        scored.append((score, record["task_id"], record["learning"]))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [learning for _, _, learning in scored[: min(top_k, len(scored))]]


def load_artifact(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_artifact(payload)
    return payload
