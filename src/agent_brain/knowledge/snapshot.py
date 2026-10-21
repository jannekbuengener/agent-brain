"""Knowledge snapshot value contracts for the Slice 6 build pipeline."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from agent_brain.contracts.versioning import require_compatible_version

KNOWLEDGE_SNAPSHOT_SCHEMA = "knowledge-snapshot/v1"
KNOWLEDGE_MANIFEST_SCHEMA = "knowledge-manifest/v1"


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


@dataclass(frozen=True, slots=True)
class BuildMetadata:
    """Deterministic build metadata describing one knowledge snapshot."""

    built_at: str
    tool_version: str
    schema_version: str = KNOWLEDGE_SNAPSHOT_SCHEMA

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="knowledge-snapshot",
            supported_major=1,
        )
        object.__setattr__(self, "built_at", _required_text(self.built_at, "built_at"))
        object.__setattr__(
            self,
            "tool_version",
            _required_text(self.tool_version, "tool_version"),
        )


@dataclass(frozen=True, slots=True)
class KnowledgeManifest:
    """Provenance entry binding a snapshot contribution to its source artifact."""

    source_ref: str
    source_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_ref",
            _required_text(self.source_ref, "source_ref"),
        )
        object.__setattr__(
            self,
            "source_hash",
            _required_text(self.source_hash, "source_hash"),
        )


@dataclass(frozen=True, slots=True)
class KnowledgeSnapshot:
    """Immutable knowledge snapshot carrying build metadata and provenance."""

    metadata: BuildMetadata
    manifests: tuple[KnowledgeManifest, ...]
    schema_version: str = KNOWLEDGE_SNAPSHOT_SCHEMA

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="knowledge-snapshot",
            supported_major=1,
        )
        if not isinstance(self.metadata, BuildMetadata):
            raise TypeError("metadata must be a BuildMetadata")
        if isinstance(self.manifests, (str, bytes)) or not isinstance(self.manifests, Sequence):
            raise TypeError("manifests must be a sequence of KnowledgeManifest values")
        for manifest in self.manifests:
            if not isinstance(manifest, KnowledgeManifest):
                raise TypeError("manifests must contain only KnowledgeManifest values")
        object.__setattr__(self, "manifests", tuple(self.manifests))
