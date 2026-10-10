"""Reject files that should not enter the public source repository."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 5 * 1024 * 1024
SKIP_DIRECTORIES = {
    ".anarres",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".uv-cache",
    ".venv",
    "__pycache__",
}
FORBIDDEN_NAMES = {".env", "credentials.json"}
FORBIDDEN_SUFFIXES = {
    ".cast",
    ".ckpt",
    ".key",
    ".log",
    ".onnx",
    ".out",
    ".pem",
    ".pt",
    ".pth",
    ".safetensors",
}
FORBIDDEN_DIRECTORIES = {"checkpoints", "mlruns", "rollouts", "traces", "wandb"}
TEXT_SUFFIXES = {
    "",
    ".cfg",
    ".ini",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
CONTENT_PATTERNS = {
    "machine-specific storage path": re.compile(r"/(?:afs|dfs|lfs)/"),
    "cluster hostname": re.compile(r"\bskampere[0-9]+\b", re.IGNORECASE),
    "Kerberos runtime configuration": re.compile(r"\bKRB5CCNAME\b"),
}
SELF = Path("tools/check_repo_hygiene.py")


def candidates() -> list[Path]:
    paths: list[Path] = []
    for directory, subdirectories, filenames in os.walk(ROOT):
        subdirectories[:] = [name for name in subdirectories if name not in SKIP_DIRECTORIES]
        base = Path(directory)
        paths.extend(base / name for name in filenames)
    return paths


def inspect(path: Path) -> list[str]:
    relative = path.relative_to(ROOT)
    problems: list[str] = []

    if path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
        problems.append(f"forbidden source file: {relative}")
    if any(part in FORBIDDEN_DIRECTORIES for part in relative.parts):
        problems.append(f"forbidden generated directory: {relative}")
    if path.stat().st_size > MAX_BYTES:
        problems.append(f"file exceeds 5 MiB: {relative}")

    if relative != SELF and path.suffix.lower() in TEXT_SUFFIXES:
        text = path.read_text(encoding="utf-8", errors="replace")
        for description, pattern in CONTENT_PATTERNS.items():
            if pattern.search(text):
                problems.append(f"{description}: {relative}")

    return problems


def main() -> int:
    problems: list[str] = []
    for path in candidates():
        problems.extend(inspect(path))

    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print(f"repository hygiene passed for {len(candidates())} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
