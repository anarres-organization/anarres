"""Read the narrow native-environment source envelope used by adapters."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


class SourceManifestError(ValueError):
    """Raised when an environment source cannot be dispatched safely."""


@dataclass(frozen=True)
class EnvironmentSource:
    """Validated source identity and its resolved native object."""

    manifest: Path
    environment_id: str
    domain: str
    adapter: str
    adapter_version: str
    native_format: str
    source: Path
    revision: str
    license: str


def _require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SourceManifestError(f"{field} must be non-empty text")
    return value.strip()


def load_source_manifest(
    path: Path,
    *,
    expected_adapter: str,
    expected_version: str,
    expected_domain: str,
    accepted_formats: tuple[str, ...],
) -> EnvironmentSource:
    """Load one local source manifest and bind it to the selected adapter."""

    manifest = path.resolve()
    if manifest.name != "anarres.toml" or not manifest.is_file():
        raise SourceManifestError(f"environment source manifest is missing: {manifest}")
    try:
        value = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise SourceManifestError(f"cannot read environment source manifest: {error}") from error
    if set(value) != {
        "schema_version",
        "environment_id",
        "domain",
        "adapter",
        "adapter_version",
        "native_format",
        "source",
    }:
        raise SourceManifestError("environment source manifest has unknown or missing fields")
    if value["schema_version"] != "anarres.environment-source.v1":
        raise SourceManifestError("unsupported environment source schema")
    source_value = value["source"]
    if not isinstance(source_value, dict) or set(source_value) != {
        "uri",
        "revision",
        "license",
    }:
        raise SourceManifestError("environment source identity has unknown or missing fields")
    adapter = _require_text(value["adapter"], "adapter")
    adapter_version = _require_text(value["adapter_version"], "adapter_version")
    domain = _require_text(value["domain"], "domain")
    native_format = _require_text(value["native_format"], "native_format")
    if adapter != expected_adapter:
        raise SourceManifestError(
            f"manifest adapter '{adapter}' does not match selected adapter '{expected_adapter}'"
        )
    if adapter_version != expected_version:
        raise SourceManifestError(
            f"manifest requires adapter {adapter_version}, installed adapter is {expected_version}"
        )
    if domain != expected_domain:
        raise SourceManifestError(
            f"manifest domain '{domain}' does not match adapter domain '{expected_domain}'"
        )
    if native_format not in accepted_formats:
        raise SourceManifestError(
            f"adapter '{adapter}' does not accept native format '{native_format}'"
        )
    uri = _require_text(source_value["uri"], "source.uri")
    if "://" in uri:
        raise SourceManifestError(
            f"adapter '{adapter}' requires a local source path, received '{uri}'"
        )
    source = (manifest.parent / uri).resolve()
    if not source.exists():
        raise SourceManifestError(f"native environment source does not exist: {source}")
    return EnvironmentSource(
        manifest=manifest,
        environment_id=_require_text(value["environment_id"], "environment_id"),
        domain=domain,
        adapter=adapter,
        adapter_version=adapter_version,
        native_format=native_format,
        source=source,
        revision=_require_text(source_value["revision"], "source.revision"),
        license=_require_text(source_value["license"], "source.license"),
    )
