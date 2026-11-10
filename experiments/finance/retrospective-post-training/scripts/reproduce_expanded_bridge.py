#!/usr/bin/env python3
"""Reproduce the frozen expanded bridge with version-stable float reductions."""

from __future__ import annotations

import builtins
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN_ANALYSIS = ROOT / "scripts" / "analyze_expanded_bridge.py"


def stable_sum(values, start=0):
    items = list(values)
    if isinstance(start, float) or any(isinstance(value, float) for value in items):
        return math.fsum([float(start), *(float(value) for value in items)])
    return builtins.sum(items, start)


def load_bridge():
    specification = importlib.util.spec_from_file_location("finance_bridge_frozen", FROZEN_ANALYSIS)
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    module.sum = stable_sum
    return module


def main() -> None:
    bridge = load_bridge()
    bridge.main()
    manifest = json.loads(bridge.MANIFEST.read_text())
    manifest[str(Path(__file__).relative_to(ROOT))] = hashlib.sha256(
        Path(__file__).read_bytes()
    ).hexdigest()
    bridge.MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
