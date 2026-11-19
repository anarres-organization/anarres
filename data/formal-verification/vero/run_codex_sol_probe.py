#!/usr/bin/env python3
"""Run the Vero development screen with GPT-5.6 Sol through OpenAI API.

Orchestrates: materialize → Docker sandbox → agent loop (OpenAI ↔ sandbox) → grade → record.

The Docker sandbox provides the containment boundary: network-denied, read-only root,
workspace-only mounts, no credentials. The controller talks to OpenAI; the sandbox cannot.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

# ── Configuration ────────────────────────────────────────────────

OPENAI_MODEL = "gpt-5.6-sol"
REASONING_EFFORT = "xhigh"
MAX_COMPLETION_TOKENS = 16384
MAX_TOKENS_PER_ATTEMPT = 200_000
MAX_WALL_SECONDS = 5400
MAX_AGENT_TURNS = 100

DEV_PANEL = [
    {"benchmark_id": "piggybank-v2", "directory": "piggybank", "specs": 23},
    {"benchmark_id": "verified-bitmasks", "directory": "VerifiedBitmasks", "specs": 124},
    {"benchmark_id": "primepy", "directory": "primepy", "specs": 9},
    {"benchmark_id": "arithmetic-v2", "directory": "Arithmetic", "specs": 191},
]

MODES: list[Literal["proof", "codeproof"]] = ["proof", "codeproof"]
ATTEMPTS_PER_REPO_MODE = 1

SANDBOX_SCRIPT = Path(__file__).resolve().parent / "serve_vibe_sandbox.py"


# ── Tool definitions for OpenAI Responses API ───────────────────

TOOLS = [
    {
        "type": "function",
        "name": "sandbox_execute",
        "description": "Execute a shell command in the sandbox workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "cwd": {
                    "type": "string",
                    "description": "Working directory (absolute path in sandbox)",
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds (optional)",
                },
            },
            "required": ["command", "cwd"],
        },
    },
    {
        "type": "function",
        "name": "sandbox_read_file",
        "description": "Read a file from the sandbox workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute path to the file in the sandbox",
                },
                "maxBytes": {
                    "type": "integer",
                    "description": "Maximum bytes to read",
                    "default": 65536,
                },
            },
            "required": ["path"],
        },
    },
]


# ── Sandbox client ───────────────────────────────────────────────


class SandboxClient:
    """JSON-RPC client for serve_vibe_sandbox.py over Unix socket."""

    def __init__(self, socket_path: str):
        self.socket_path = socket_path
        self._id = 0

    def _call(self, method: str, params: dict) -> dict:
        self._id += 1
        request = json.dumps({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params})
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(self.socket_path)
            sock.sendall((request + "\n").encode("utf-8"))
            sock.shutdown(socket.SHUT_WR)
            chunks = []
            while True:
                chunk = sock.recv(16 * 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            data = b"".join(chunks)
            return json.loads(data)
        finally:
            sock.close()

    def initialize(self) -> dict:
        return self._call("agent/initialize", {"protocolVersion": 2})

    def execute(self, command: str, cwd: str, timeout: float | None = None) -> dict:
        params: dict[str, Any] = {"command": command, "cwd": cwd}
        if timeout is not None:
            params["timeout"] = timeout
        return self._call("sandbox/execute", params)

    def read_file(self, path: str, max_bytes: int = 65536) -> dict:
        return self._call("sandbox/readFile", {"path": path, "maxBytes": max_bytes})


# ── OpenAI Responses API client ─────────────────────────────────


def openai_responses(
    input_items: list[dict],
    *,
    api_key: str,
    api_base: str = "https://api.openai.com/v1",
) -> dict:
    """Call OpenAI Responses API with reasoning effort and tools."""
    import urllib.error
    import urllib.request

    payload: dict[str, Any] = {
        "model": OPENAI_MODEL,
        "input": input_items,
        "tools": TOOLS,
        "reasoning": {"effort": REASONING_EFFORT},
        "max_output_tokens": MAX_COMPLETION_TOKENS,
        "store": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base}/responses",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=1800) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = ""
        with contextlib.suppress(Exception):
            body = exc.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"OpenAI HTTP {exc.code}: {body}") from exc


# ── Context window management ────────────────────────────────────

CHARS_PER_TOKEN_ESTIMATE = 3.5
MAX_CONTEXT_TOKENS = 128_000
CONTEXT_BUDGET = MAX_CONTEXT_TOKENS - MAX_COMPLETION_TOKENS - 4000


def estimate_item_tokens(item: dict) -> int:
    text = ""
    if isinstance(item.get("content"), str):
        text = item["content"]
    elif isinstance(item.get("content"), list):
        for part in item["content"]:
            if isinstance(part, dict) and part.get("text"):
                text += part["text"]
    if item.get("arguments"):
        text += item["arguments"]
    if item.get("output"):
        text += item["output"]
    if item.get("name"):
        text += item["name"]
    return max(8, int(len(text) / CHARS_PER_TOKEN_ESTIMATE) + 8)


def trim_context(input_items: list[dict], aggressive: bool = False) -> None:
    budget = CONTEXT_BUDGET if not aggressive else CONTEXT_BUDGET - 8000
    total = sum(estimate_item_tokens(item) for item in input_items)
    if total <= budget:
        return
    keep_tail = 8 if not aggressive else 4
    i = 2
    while i < len(input_items) - keep_tail and total > budget:
        item = input_items[i]
        if item.get("type") == "function_call_output":
            old_len = estimate_item_tokens(item)
            item["output"] = "[trimmed]"
            total -= old_len - estimate_item_tokens(item)
        i += 1


# ── Agent loop ───────────────────────────────────────────────────


@dataclass
class AttemptResult:
    attempt_id: str
    benchmark_id: str
    mode: str
    attempt_index: int
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_output_tokens: int = 0
    tool_calls: int = 0
    wall_seconds: float = 0.0
    stop_reason: str = ""
    infrastructure_errors: list[str] = field(default_factory=list)
    grade: dict | None = None
    sandbox_receipt: dict | None = None


def _execute_tool(
    name: str,
    args: dict,
    sandbox: SandboxClient,
    workspace_path: str,
) -> str:
    """Dispatch a tool call to the sandbox and return a string result."""
    if name == "sandbox_execute":
        rpc_resp = sandbox.execute(
            args["command"],
            args.get("cwd", workspace_path),
            args.get("timeout"),
        )
    elif name == "sandbox_read_file":
        rpc_resp = sandbox.read_file(args["path"], args.get("maxBytes", 65536))
    else:
        return f"Error: unknown tool: {name}"

    if "result" in rpc_resp:
        content = rpc_resp["result"]
        if name == "sandbox_read_file" and isinstance(content, dict):
            b64 = content.get("contentBase64")
            if b64:
                try:
                    content = base64.b64decode(b64).decode("utf-8", errors="replace")
                except Exception:
                    content = f"[base64 content, {len(b64)} chars]"
            else:
                content = "[file not found]"
    elif "error" in rpc_resp:
        content = f"Error: {rpc_resp['error'].get('message', str(rpc_resp['error']))}"
    else:
        content = json.dumps(rpc_resp)

    if isinstance(content, dict):
        content = json.dumps(content)
    return str(content)[:8_000]


def run_agent_loop(
    instruction: str,
    sandbox: SandboxClient,
    workspace_path: str,
    result: AttemptResult,
    api_key: str,
    transcript_path: Path | None = None,
) -> None:
    system_prompt = (
        "You are a Lean 4 proof engineer. You have access to a sandbox with a "
        "Lean project. Your workspace is at " + workspace_path + ".\n\n"
        "## Tools\n"
        "Use `sandbox_execute` to run shell commands and `sandbox_read_file` "
        "to read files. Edit files by writing content with shell commands like "
        "`cat > path << 'EOF'\\n...\\nEOF` or using sed.\n\n"
        "## Critical workflow rules\n"
        "1. **Read INSTRUCTION.md first** — it specifies the task, file layout, "
        "marker grammar, and grading rules. Follow it precisely.\n"
        "2. **Read all Spec files** before writing any proof.\n"
        "3. **Compile after every proof** with `lake lean <path>`. Fix errors "
        "immediately. Never batch multiple proofs without compiling between them.\n"
        "4. **One spec at a time.** Fill a stub, compile, fix, then move to the next. "
        "A compiling proof is locked-in progress — never revert it.\n"
        "5. **If a proof fails to compile after two strategies, skip it** and move to "
        "the next spec. Come back later.\n\n"
        "## Environment constraints\n"
        "- The `lake` and `lean` binaries are NOT on the default PATH. Use the full "
        "path: `/opt/elan/bin/lake` and `/opt/elan/bin/lean`. Or run "
        "`export PATH=/opt/elan/bin:$PATH` at the start of each command.\n"
        "- The sandbox has Lean 4 core (`Init`, `Lean`) and `Lake`. There is NO `Std` "
        "library. **Never write `import Std` or `import Std.Tactic.Omega` or any "
        "`Std.*` import.** The `omega` tactic is available from core `Init.Omega` "
        "(auto-imported) — you do NOT need to import it. The `imports` slot should "
        "normally be left empty.\n"
        "- `lake build` only builds modules in the lakefile — it does NOT build or "
        "check proof files. You MUST run `lake lean Primepy/Proof/Primes.lean` "
        "(or the equivalent path) to see if proofs compile. This is the single most "
        "important command. Run it after every change.\n\n"
        "## Common Lean 4 pitfalls\n"
        "- `omega` cannot reason about `Int.ofNat` coercions between `Int` and `Nat`. "
        "Use `simp only [Int.ofNat]` or `push_cast` to normalize before `omega`.\n"
        "- For Int/Nat mixed goals, prefer `norm_cast` or `push_cast` before `omega`.\n"
        "- `grind` is experimental and often fails — prefer `simp`, `omega`, `decide`, "
        "`norm_num` as primary closers.\n"
        "- For list-based specs, decompose with helper lemmas proved by structural "
        "induction, not monolithic tactic blocks.\n"
    )

    input_items: list[dict] = [
        {"role": "developer", "content": system_prompt},
        {"role": "user", "content": instruction},
    ]

    transcript_fh = None
    if transcript_path:
        transcript_fh = open(transcript_path, "w")  # noqa: SIM115 - closed after the loop

    def _log_transcript(entry: dict) -> None:
        if transcript_fh:
            transcript_fh.write(json.dumps(entry) + "\n")
            transcript_fh.flush()

    start = time.monotonic()
    cumulative_output = 0

    for turn in range(MAX_AGENT_TURNS):
        elapsed = time.monotonic() - start
        if elapsed > MAX_WALL_SECONDS:
            result.stop_reason = "wall_time_limit"
            break
        if cumulative_output > MAX_TOKENS_PER_ATTEMPT:
            result.stop_reason = "token_limit"
            break

        trim_context(input_items)
        try:
            response = openai_responses(input_items, api_key=api_key)
        except RuntimeError as exc:
            if "context_length_exceeded" in str(exc).lower():
                trim_context(input_items, aggressive=True)
                try:
                    response = openai_responses(input_items, api_key=api_key)
                except Exception as exc2:
                    result.infrastructure_errors.append(
                        f"openai (after trim): {type(exc2).__name__}: {exc2}"
                    )
                    result.stop_reason = "infrastructure_error"
                    break
            else:
                result.infrastructure_errors.append(f"openai: {type(exc).__name__}: {exc}")
                result.stop_reason = "infrastructure_error"
                break
        except Exception as exc:
            result.infrastructure_errors.append(f"openai: {type(exc).__name__}: {exc}")
            result.stop_reason = "infrastructure_error"
            break

        usage = response.get("usage", {})
        result.input_tokens += usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        result.output_tokens += output_tokens
        result.cached_input_tokens += usage.get("input_tokens_details", {}).get("cached_tokens", 0)
        result.reasoning_output_tokens += usage.get("output_tokens_details", {}).get(
            "reasoning_tokens", 0
        )
        cumulative_output += output_tokens
        result.turns = turn + 1

        output_items = response.get("output", [])
        function_calls = [item for item in output_items if item.get("type") == "function_call"]

        # Log assistant output
        for oi in output_items:
            if oi.get("type") == "message":
                for part in oi.get("content", []):
                    if part.get("type") == "output_text":
                        _log_transcript(
                            {"turn": turn, "role": "assistant", "text": part["text"][:2000]}
                        )
            elif oi.get("type") == "function_call":
                _log_transcript(
                    {
                        "turn": turn,
                        "role": "tool_call",
                        "name": oi.get("name"),
                        "args": oi.get("arguments", "")[:500],
                    }
                )

        if not function_calls:
            result.stop_reason = response.get("stop_reason", "stop")
            break

        input_items.extend(output_items)

        for fc in function_calls:
            result.tool_calls += 1
            name = fc.get("name", "")
            call_id = fc.get("call_id", "")
            try:
                args = json.loads(fc.get("arguments", "{}"))
            except json.JSONDecodeError:
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps({"error": "invalid JSON arguments"}),
                    }
                )
                continue

            try:
                tool_output = _execute_tool(name, args, sandbox, workspace_path)
            except Exception as exc:
                tool_output = f"Sandbox error: {type(exc).__name__}: {exc}"
                result.infrastructure_errors.append(f"sandbox_{name}: {exc}")

            _log_transcript(
                {"turn": turn, "role": "tool_result", "name": name, "output": tool_output[:1000]}
            )
            input_items.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": tool_output,
                }
            )
    else:
        result.stop_reason = "max_turns"

    result.wall_seconds = time.monotonic() - start
    if transcript_fh:
        transcript_fh.close()


# ── Probe orchestrator ────────────────────────────────────────────


def materialize_sandbox(
    vero_root: Path,
    vero_python: str,
    benchmark_id: str,
    benchmark_dir_name: str,
    mode: str,
    output_dir: Path,
) -> Path:
    benchmark_dir = vero_root / "benchmarks" / benchmark_dir_name
    sandbox_dir = output_dir / "source"
    cmd = [
        vero_python,
        "-c",
        f"""
import sys
sys.path.insert(0, "{vero_root / "src"}")
from pathlib import Path
from vero.generation.sandbox import create_sandbox

result = create_sandbox(
    benchmark_dir=Path("{benchmark_dir}"),
    sandbox_dir=Path("{sandbox_dir}"),
    mode="{mode}",
    overwrite=False,
    strip_manifest=True,
    source_context="lean",
)
print("OK", result.sandbox_dir)
""",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(f"Vero materialize failed: {proc.stderr[:2000]}")
    if not sandbox_dir.exists():
        candidates = list(output_dir.rglob("INSTRUCTION.md"))
        if candidates:
            sandbox_dir = candidates[0].parent
        else:
            raise RuntimeError(f"No sandbox found in {output_dir}")
    return sandbox_dir


def grade_attempt(
    vero_root: Path,
    vero_python: str,
    benchmark_dir: Path,
    source_dir: Path,
    mode: str,
    eval_dir: Path,
) -> dict:
    cmd = [
        vero_python,
        "-c",
        f"""
import json, sys
sys.path.insert(0, "{vero_root / "src"}")
from pathlib import Path
from vero.generation.benchmark import Benchmark
from vero.generation.extractor import extract
from vero.evaluation.runner import run_evaluation

source_dir = Path("{source_dir}")
benchmark_dir = Path("{benchmark_dir}")
eval_dir = Path("{eval_dir}")
mode = "{mode}"

bench = Benchmark(benchmark_dir)
artifact = extract(source_dir, bench, mode=mode)
result = run_evaluation(
    benchmark_dir=benchmark_dir,
    artifact=artifact,
    mode=mode,
    eval_sandbox_dir=eval_dir / "eval_sandbox",
    report_dir=eval_dir / "eval_report",
    lake_timeout=300,
)
report = result.report
print(json.dumps({{
    "total_specs": report.summary.total_specs,
    "passed_specs": report.summary.passed_specs,
    "unfilled_specs": report.summary.unfilled_specs,
    "failed_specs": report.summary.failed_specs,
    "build_ok": report.build_ok,
    "specs": [
        {{"module": s.module, "spec": s.spec, "status": s.status}}
        for s in report.specs
    ],
}}))
""",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        return {
            "error": result.stderr[:2000],
            "build_ok": False,
            "passed_specs": 0,
            "total_specs": 0,
        }
    try:
        return json.loads(result.stdout.strip().split("\n")[-1])
    except (json.JSONDecodeError, IndexError):
        return {
            "error": f"parse failure: {result.stdout[:500]}",
            "build_ok": False,
            "passed_specs": 0,
            "total_specs": 0,
        }


def run_one_attempt(
    vero_root: Path,
    vero_python: str,
    docker_image: str,
    benchmark_id: str,
    benchmark_dir_name: str,
    mode: str,
    attempt_index: int,
    probe_root: Path,
    api_key: str,
    inference_config_digest: str,
) -> AttemptResult:
    attempt_id = f"{benchmark_id}_{mode}_a{attempt_index}_{secrets.token_hex(4)}"
    attempt_dir = probe_root / attempt_id
    attempt_dir.mkdir(parents=True, exist_ok=True)

    result = AttemptResult(
        attempt_id=attempt_id,
        benchmark_id=benchmark_id,
        mode=mode,
        attempt_index=attempt_index,
    )

    print(f"\n{'=' * 60}")
    print(f"  Attempt: {attempt_id}")
    print(f"  Benchmark: {benchmark_id} | Mode: {mode} | Index: {attempt_index}")
    print(f"{'=' * 60}")

    # 1. Materialize sandbox
    print("  [1/4] Materializing sandbox...")
    try:
        source_dir = materialize_sandbox(
            vero_root,
            vero_python,
            benchmark_id,
            benchmark_dir_name,
            mode,
            attempt_dir / "run",
        )
    except Exception as exc:
        result.infrastructure_errors.append(f"materialize: {exc}")
        result.stop_reason = "infrastructure_error"
        print(f"  FAILED: {exc}")
        return result

    print(f"  Sandbox at: {source_dir}")

    # Make workspace world-writable so container root (with --cap-drop ALL) can write
    subprocess.run(["chmod", "-R", "a+rw", str(source_dir)], check=True)
    for d in source_dir.rglob("*"):
        if d.is_dir():
            d.chmod(0o777)

    # 2. Start sandbox server
    print("  [2/4] Starting sandbox server...")
    # Unix sockets limited to 107 bytes; use /tmp to keep path short.
    # serve_vibe_sandbox.py requires the parent dir to not exist (it creates it).
    socket_dir = Path(f"/tmp/vero-{attempt_id[:12]}")
    if socket_dir.exists():
        shutil.rmtree(socket_dir)
    socket_path = socket_dir / "s.sock"
    receipt_path = attempt_dir / "sandbox_receipt.json"
    sandbox_log = attempt_dir / "sandbox_server.log"

    with open(sandbox_log, "w") as sandbox_log_fh:
        sandbox_proc = subprocess.Popen(
            [
                vero_python,
                str(SANDBOX_SCRIPT),
                "--socket",
                str(socket_path),
                "--image",
                docker_image,
                "--workspace",
                str(source_dir),
                "--receipt",
                str(receipt_path),
                "--attempt-id",
                attempt_id,
                "--task-id",
                benchmark_id,
                "--model-artifact-digest",
                f"sha256:{hashlib.sha256(OPENAI_MODEL.encode()).hexdigest()}",
                "--inference-config-digest",
                inference_config_digest,
                "--maximum-command-seconds",
                "300",
                "--memory",
                "16g",
                "--cpus",
                "4",
                "--pids",
                "256",
                "--user",
                "0:0",
            ],
            stdout=sandbox_log_fh,
            stderr=subprocess.STDOUT,
        )

    for _ in range(60):
        if socket_path.exists():
            break
        if sandbox_proc.poll() is not None:
            log_tail = sandbox_log.read_text()[-2000:] if sandbox_log.exists() else "no log"
            result.infrastructure_errors.append(f"sandbox server exited early: {log_tail}")
            result.stop_reason = "infrastructure_error"
            print(f"  FAILED: sandbox server died. Log:\n{log_tail[:500]}")
            return result
        time.sleep(0.5)
    else:
        log_tail = sandbox_log.read_text()[-2000:] if sandbox_log.exists() else "no log"
        result.infrastructure_errors.append(f"sandbox socket did not appear within 30s: {log_tail}")
        result.stop_reason = "infrastructure_error"
        sandbox_proc.terminate()
        sandbox_proc.wait(timeout=10)
        print(f"  FAILED: socket timeout. Log:\n{log_tail[:500]}")
        return result

    sandbox = SandboxClient(str(socket_path))

    try:
        init_resp = sandbox.initialize()
        workspace_path = init_resp.get("result", {}).get("workspace", "/workspace")
    except Exception as exc:
        result.infrastructure_errors.append(f"sandbox init: {exc}")
        result.stop_reason = "infrastructure_error"
        sandbox_proc.terminate()
        sandbox_proc.wait(timeout=10)
        print(f"  FAILED: sandbox init: {exc}")
        return result

    print(f"  Sandbox ready, workspace: {workspace_path}")

    try:
        instr_resp = sandbox.read_file(f"{workspace_path}/INSTRUCTION.md", 100_000)
        instr_b64 = instr_resp.get("result", {}).get("contentBase64", "")
        instruction = base64.b64decode(instr_b64).decode("utf-8") if instr_b64 else ""
    except Exception:
        instruction = "Read INSTRUCTION.md in the workspace and follow its directions."

    # 3. Run agent loop
    print(f"  [3/4] Running agent loop (max {MAX_AGENT_TURNS} turns, {MAX_WALL_SECONDS}s)...")
    transcript_path = attempt_dir / "transcript.jsonl"
    run_agent_loop(instruction, sandbox, workspace_path, result, api_key, transcript_path)
    print(
        f"  Agent done: {result.turns} turns, {result.output_tokens} output tokens "
        f"({result.reasoning_output_tokens} reasoning), "
        f"{result.tool_calls} tool calls, {result.wall_seconds:.1f}s, "
        f"stop={result.stop_reason}"
    )

    sandbox_proc.terminate()
    try:
        sandbox_proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        sandbox_proc.kill()
        sandbox_proc.wait()

    shutil.rmtree(socket_dir, ignore_errors=True)

    if receipt_path.exists():
        result.sandbox_receipt = json.loads(receipt_path.read_text())

    # 4. Grade
    print("  [4/4] Grading...")
    try:
        benchmark_dir = vero_root / "benchmarks" / benchmark_dir_name
        grade = grade_attempt(
            vero_root,
            vero_python,
            benchmark_dir,
            source_dir,
            mode,
            attempt_dir / "eval",
        )
        result.grade = grade
        passed = grade.get("passed_specs", 0)
        total = grade.get("total_specs", 0)
        print(f"  Grade: {passed}/{total} specs passed, build_ok={grade.get('build_ok')}")
    except Exception as exc:
        result.infrastructure_errors.append(f"grade: {exc}")
        print(f"  Grade FAILED: {exc}")

    return result


def compute_inference_config_digest(config_path: Path) -> str:
    content = config_path.read_bytes()
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def main():
    parser = argparse.ArgumentParser(description="Run Vero development screen with GPT-5.6 Sol")
    parser.add_argument("--vero-root", type=Path, required=True)
    parser.add_argument(
        "--vero-python", type=str, required=True, help="Path to the Vero Python interpreter"
    )
    parser.add_argument("--probe-root", type=Path, required=True)
    parser.add_argument(
        "--docker-image", type=str, required=True, help="Docker image digest (sha256:...)"
    )
    parser.add_argument(
        "--smoke-test", action="store_true", help="Run 1 attempt only (primepy proof)"
    )
    parser.add_argument("--benchmark", type=str, default=None, help="Run only this benchmark_id")
    parser.add_argument(
        "--mode", type=str, default=None, help="Run only this mode (proof or codeproof)"
    )
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    vero_root = args.vero_root.resolve()
    probe_root = args.probe_root.resolve()
    probe_root.mkdir(parents=True, exist_ok=True)

    inference_config = Path(__file__).resolve().parent / "inference-config-codex-sol.v1.json"
    inference_config_digest = compute_inference_config_digest(inference_config)

    # Verify OpenAI API is reachable
    print(f"Model: {OPENAI_MODEL}, reasoning_effort: {REASONING_EFFORT}")
    try:
        import urllib.request

        req = urllib.request.Request(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        models = json.loads(resp.read())
        available = [
            m["id"] for m in models["data"] if "sol" in m["id"].lower() or "5.6" in m["id"]
        ]
        print(f"OpenAI reachable. Matching models: {available[:5]}")
    except Exception as exc:
        print(f"WARNING: OpenAI model check failed: {exc}")
        print("Proceeding anyway — will fail on first completion if unreachable.")

    all_results: list[AttemptResult] = []

    if args.smoke_test:
        attempts = [(DEV_PANEL[2], "proof", 0)]  # primepy proof
    else:
        attempts = [
            (repo, mode, idx)
            for repo in DEV_PANEL
            for mode in MODES
            for idx in range(ATTEMPTS_PER_REPO_MODE)
        ]

    if args.benchmark:
        attempts = [(r, m, i) for r, m, i in attempts if r["benchmark_id"] == args.benchmark]
    if args.mode:
        attempts = [(r, m, i) for r, m, i in attempts if m == args.mode]

    print(f"\nDevelopment screen: {len(attempts)} attempts")
    print(f"Docker image: {args.docker_image}")
    print(f"Probe root: {probe_root}\n")

    for i, (repo, mode, idx) in enumerate(attempts):
        print(f"\n[{i + 1}/{len(attempts)}]")
        result = run_one_attempt(
            vero_root=vero_root,
            vero_python=args.vero_python,
            docker_image=args.docker_image,
            benchmark_id=repo["benchmark_id"],
            benchmark_dir_name=repo["directory"],
            mode=mode,
            attempt_index=idx,
            probe_root=probe_root,
            api_key=api_key,
            inference_config_digest=inference_config_digest,
        )
        all_results.append(result)

        results_path = probe_root / "results.jsonl"
        with open(results_path, "a") as f:
            f.write(
                json.dumps(
                    {
                        "attempt_id": result.attempt_id,
                        "benchmark_id": result.benchmark_id,
                        "mode": result.mode,
                        "attempt_index": result.attempt_index,
                        "turns": result.turns,
                        "input_tokens": result.input_tokens,
                        "output_tokens": result.output_tokens,
                        "cached_input_tokens": result.cached_input_tokens,
                        "reasoning_output_tokens": result.reasoning_output_tokens,
                        "tool_calls": result.tool_calls,
                        "wall_seconds": round(result.wall_seconds, 2),
                        "stop_reason": result.stop_reason,
                        "infrastructure_errors": result.infrastructure_errors,
                        "grade": result.grade,
                    }
                )
                + "\n"
            )

    # Summary
    total_passed = sum(r.grade.get("passed_specs", 0) for r in all_results if r.grade)
    total_specs = sum(r.grade.get("total_specs", 0) for r in all_results if r.grade)
    repos_with_nonzero = set()
    for r in all_results:
        if r.grade and r.grade.get("passed_specs", 0) > 0:
            repos_with_nonzero.add(r.benchmark_id)

    print(f"\n{'=' * 60}")
    print("  SCREEN RESULTS")
    print(f"{'=' * 60}")
    print(f"  Total: {total_passed}/{total_specs} specs passed")
    print(
        f"  Repos with nonzero strict coverage: {len(repos_with_nonzero)} "
        f"({', '.join(sorted(repos_with_nonzero)) or 'none'})"
    )
    print(
        f"  Infrastructure errors: "
        f"{sum(1 for r in all_results if r.infrastructure_errors)}/{len(all_results)} attempts"
    )

    pooled_rate = total_passed / total_specs if total_specs > 0 else 0.0
    print(f"  Pooled strict success rate: {pooled_rate:.3f}")

    screen_pass = (
        all(not r.infrastructure_errors for r in all_results)
        and len(repos_with_nonzero) >= 2
        and pooled_rate < 0.80
    )
    print(f"\n  Screen {'PASSES' if screen_pass else 'does not pass'}")

    summary = {
        "probe_id": f"vero-codex-sol-dev-screen-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
        "model": OPENAI_MODEL,
        "reasoning_effort": REASONING_EFFORT,
        "harness": "anarres/vero-codex-sol-harness@1.0.0",
        "total_attempts": len(all_results),
        "successful_attempts": sum(1 for r in all_results if not r.infrastructure_errors),
        "total_passed_specs": total_passed,
        "total_specs": total_specs,
        "repos_with_nonzero_coverage": sorted(repos_with_nonzero),
        "pooled_strict_rate": round(pooled_rate, 4),
        "screen_pass": screen_pass,
        "per_attempt": [
            {
                "attempt_id": r.attempt_id,
                "benchmark_id": r.benchmark_id,
                "mode": r.mode,
                "turns": r.turns,
                "output_tokens": r.output_tokens,
                "reasoning_output_tokens": r.reasoning_output_tokens,
                "tool_calls": r.tool_calls,
                "wall_seconds": round(r.wall_seconds, 2),
                "stop_reason": r.stop_reason,
                "passed_specs": r.grade.get("passed_specs", 0) if r.grade else 0,
                "total_specs": r.grade.get("total_specs", 0) if r.grade else 0,
                "infrastructure_errors": r.infrastructure_errors,
            }
            for r in all_results
        ],
    }

    summary_path = probe_root / "probe_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"\n  Summary written to: {summary_path}")


if __name__ == "__main__":
    main()
