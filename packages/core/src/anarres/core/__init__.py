"""Shared contracts and identifiers for Anarres."""

from .adapter_protocol import ADAPTER_PROTOCOL_VERSION, consume_adapter_invocation
from .artifacts import ArtifactReference
from .hashing import canonical_json_bytes, sha256_digest
from .source_manifest import EnvironmentSource, SourceManifestError, load_source_manifest

__all__ = [
    "ADAPTER_PROTOCOL_VERSION",
    "ArtifactReference",
    "EnvironmentSource",
    "SourceManifestError",
    "canonical_json_bytes",
    "consume_adapter_invocation",
    "load_source_manifest",
    "sha256_digest",
]
