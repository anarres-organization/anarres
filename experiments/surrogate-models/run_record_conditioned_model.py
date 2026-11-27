#!/usr/bin/env python3
"""Run frozen record-conditioned prompts through an OpenAI-compatible server."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
INPUTS = HERE / "RECORD_CONDITIONED_INPUTS.jsonl"
CONTRACT = HERE / "RECORD_CONDITIONED_CONTRACT.json"
DEFAULT_OUTPUT = HERE / "RECORD_CONDITIONED_PREDICTIONS.jsonl"
DEFAULT_RECEIPT = HERE / "RECORD_CONDITIONED_PREDICTION_RECEIPT.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        stripped = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError as error:
        start, end = stripped.find("{"), stripped.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("model response contains no JSON object") from error
        value = json.loads(stripped[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("model response must be a JSON object")
    return value


def validate_prediction(value: dict[str, Any], expected: set[str]) -> dict[str, Any]:
    scores = value.get("candidate_scores")
    if not isinstance(scores, dict) or set(scores) != expected:
        raise ValueError("candidate_scores do not exactly match the target candidates")
    clean_scores = {}
    for key, score in scores.items():
        number = float(score)
        if not 0 <= number <= 1:
            raise ValueError("candidate scores must be in [0,1]")
        clean_scores[key] = number
    order = value.get("predicted_order")
    if not isinstance(order, list) or set(order) != expected or len(order) != len(expected):
        order = sorted(expected, key=lambda key: (-clean_scores[key], key))
    confidence = float(value.get("confidence", 0.0))
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be in [0,1]")
    return {
        "candidate_scores": clean_scores,
        "predicted_order": order,
        "abstain": bool(value.get("abstain", False)),
        "confidence": confidence,
        "evidence_summary": str(value.get("evidence_summary", ""))[:2000],
    }


def neutral_abstention(expected: set[str], error: str) -> dict[str, Any]:
    """Return the frozen conservative score for an exhausted serving failure."""
    keys = sorted(expected)
    return {
        "candidate_scores": {key: 0.5 for key in keys},
        "predicted_order": keys,
        "abstain": True,
        "confidence": 0.0,
        "evidence_summary": f"No valid final JSON after the retry limit: {error}"[:2000],
    }


def request_payload(
    model: str,
    row: dict[str, Any],
    max_tokens: int,
    reasoning_effort: str,
    expected: set[str],
    seed: int,
) -> dict[str, Any]:
    keys = sorted(expected)
    schema = {
        "type": "object",
        "properties": {
            "candidate_scores": {
                "type": "object",
                "properties": {key: {"type": "number", "minimum": 0, "maximum": 1} for key in keys},
                "required": keys,
                "additionalProperties": False,
            },
            "predicted_order": {
                "type": "array",
                "items": {"type": "string", "enum": keys},
                "minItems": len(keys),
                "maxItems": len(keys),
            },
            "abstain": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "evidence_summary": {"type": "string"},
        },
        "required": [
            "candidate_scores",
            "predicted_order",
            "abstain",
            "confidence",
            "evidence_summary",
        ],
        "additionalProperties": False,
    }
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": row["system"]},
            {"role": "user", "content": row["user"]},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "reasoning_effort": reasoning_effort,
        "seed": seed,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "candidate_ranking",
                "strict": True,
                "schema": schema,
            },
        },
    }


def request_prediction(
    base_url: str,
    model: str,
    row: dict[str, Any],
    max_tokens: int,
    reasoning_effort: str,
    seed: int,
    max_attempts: int,
    failure_policy: str = "raise",
) -> tuple[dict[str, Any], dict[str, Any]]:
    expected = {item["candidate_key"] for item in json.loads(row["user"])["target_candidates"]}
    payload = request_payload(model, row, max_tokens, reasoning_effort, expected, seed)
    attempts = []
    parsed = None
    terminal_failure = None
    for attempt in range(1, max_attempts + 1):
        request = urllib.request.Request(
            base_url.rstrip("/") + "/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        started = time.monotonic()
        with urllib.request.urlopen(request, timeout=900) as response:
            body = json.loads(response.read())
        elapsed = time.monotonic() - started
        message = body["choices"][0]["message"]
        content = message.get("content") or message.get("final") or ""
        usage = body.get("usage", {})
        record = {
            "attempt": attempt,
            "elapsed_seconds": elapsed,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "finish_reason": body["choices"][0].get("finish_reason"),
        }
        try:
            parsed = validate_prediction(extract_json(content), expected)
        except (ValueError, json.JSONDecodeError) as error:
            record["validation_error"] = str(error)
            attempts.append(record)
            if attempt == max_attempts:
                if failure_policy != "neutral_abstention":
                    raise ValueError("model failed to return valid final JSON") from error
                terminal_failure = str(error)
                parsed = neutral_abstention(expected, terminal_failure)
                break
            continue
        attempts.append(record)
        break
    assert parsed is not None
    metadata = {
        "attempts": attempts,
        "elapsed_seconds": sum(item["elapsed_seconds"] for item in attempts),
        "prompt_tokens": sum(item["prompt_tokens"] or 0 for item in attempts),
        "completion_tokens": sum(item["completion_tokens"] or 0 for item in attempts),
        "total_tokens": sum(item["total_tokens"] or 0 for item in attempts),
        "finish_reason": attempts[-1]["finish_reason"],
        "terminal_failure": terminal_failure,
    }
    return parsed, metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    contract = json.loads(CONTRACT.read_text())
    model = args.model or contract["model"]["model_id"]
    rows = [json.loads(line) for line in INPUTS.read_text().splitlines() if line]
    if args.limit is not None:
        rows = rows[: args.limit]
    completed = {}
    if args.resume and args.output.exists():
        completed = {
            row["prompt_id"]: row
            for row in (json.loads(line) for line in args.output.read_text().splitlines() if line)
        }
    output_rows = []
    for index, row in enumerate(rows, 1):
        if row["prompt_id"] in completed:
            output_rows.append(completed[row["prompt_id"]])
            continue
        prediction, usage = request_prediction(
            args.base_url,
            model,
            row,
            int(contract["model"]["max_output_tokens"]),
            contract["model"]["reasoning_effort"],
            int(contract["model"]["seed"]),
            int(contract["model"]["max_attempts"]),
            contract["model"].get("failure_policy", "raise"),
        )
        output_rows.append(
            {
                "prompt_id": row["prompt_id"],
                "condition": row["condition"],
                "heldout_study": row["heldout_study"],
                "target_panel": row["target_panel"],
                "model": model,
                "prediction": prediction,
                "usage": usage,
            }
        )
        args.output.write_text("".join(canonical(item) + "\n" for item in output_rows))
        print(f"[{index}/{len(rows)}] {row['condition']} {row['target_panel']}", flush=True)
    receipt = {
        "artifact": "anarres_record_conditioned_prediction_receipt_v1",
        "status": "predictions written before protected-label scoring",
        "contract_sha256": sha256(CONTRACT),
        "inputs_sha256": sha256(INPUTS),
        "predictions_sha256": sha256(args.output),
        "rows": len(output_rows),
        "model": model,
        "revision": contract["model"]["revision"],
        "reasoning_effort": contract["model"]["reasoning_effort"],
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
