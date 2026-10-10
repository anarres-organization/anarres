"""References to artifacts stored outside the source repository."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    """An immutable reference to a dataset, model, result, or other artifact."""

    uri: str
    sha256: str
    media_type: str
    size_bytes: int
    license: str
    producing_run: str | None = None

    def __post_init__(self) -> None:
        if not self.uri:
            raise ValueError("artifact URI must not be empty")
        if not self.sha256.startswith("sha256:") or len(self.sha256) != 71:
            raise ValueError("sha256 must be a prefixed 64-character digest")
        if self.size_bytes < 0:
            raise ValueError("size_bytes must be non-negative")
        if not self.license:
            raise ValueError("artifact license must not be empty")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
