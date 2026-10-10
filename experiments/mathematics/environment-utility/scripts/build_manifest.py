#!/usr/bin/env python3
"""Create a deterministic SHA-256 manifest for the release."""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "MANIFEST.sha256"


def main() -> None:
    paths = sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file() and path != OUTPUT and "__pycache__" not in path.parts
    )
    lines = []
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(ROOT).as_posix()}")
    OUTPUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUTPUT.name} ({len(lines)} files)")


if __name__ == "__main__":
    main()
