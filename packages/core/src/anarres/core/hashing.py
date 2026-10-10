"""Deterministic serialization and content identifiers."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON data deterministically for hashing and freezing."""

    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_digest(value: Any) -> str:
    """Return a prefixed SHA-256 digest for canonical JSON data."""

    return f"sha256:{hashlib.sha256(canonical_json_bytes(value)).hexdigest()}"
