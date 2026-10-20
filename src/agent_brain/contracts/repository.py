"""Product-neutral repository source, profile, and artifact contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from agent_brain.contracts.versioning import require_compatible_version

REPOSITORY_SOURCE_SCHEMA = "repository-source/v1"
REPOSITORY_PROFILE_SCHEMA = "repository-profile/v1"
ARTIFACT_REF_SCHEMA = "artifact-ref/v1"


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def _optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field_name)


def _text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple or list of strings")
    return tuple(_required_text(item, field_name) for item in values)


@dataclass(frozen=True, slots=True)
class RepositorySource:
    """Stable identity for one repository source at an optional revision."""

    schema_version: str
    source_id: str
    repository: str
    revision: str | None = None
    source_uri: str | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="repository-source",
            supported_major=1,
        )
        object.__setattr__(self, "source_id", _required_text(self.source_id, "source_id"))
        object.__setattr__(self, "repository", _required_text(self.repository, "repository"))
        object.__setattr__(self, "revision", _optional_text(self.revision, "revision"))
        object.__setattr__(self, "source_uri", _optional_text(self.source_uri, "source_uri"))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "source_id": self.source_id,
            "repository": self.repository,
        }
        if self.revision is not None:
            payload["revision"] = self.revision
        if self.source_uri is not None:
            payload["source_uri"] = self.source_uri
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RepositorySource:
        return cls(
            schema_version=payload.get("schema_version", ""),
            source_id=payload.get("source_id", ""),
            repository=payload.get("repository", ""),
            revision=payload.get("revision"),
            source_uri=payload.get("source_uri"),
        )


@dataclass(frozen=True, slots=True)
class RepositoryProfile:
    """Generic repository ingestion boundaries without product policy."""

    schema_version: str
    profile_id: str
    source: RepositorySource
    include_paths: tuple[str, ...] = ()
    exclude_paths: tuple[str, ...] = ()
    allowed_file_types: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="repository-profile",
            supported_major=1,
        )
        object.__setattr__(self, "profile_id", _required_text(self.profile_id, "profile_id"))
        if not isinstance(self.source, RepositorySource):
            raise TypeError("source must be a RepositorySource")
        object.__setattr__(
            self,
            "include_paths",
            _text_tuple(self.include_paths, "include_paths"),
        )
        object.__setattr__(
            self,
            "exclude_paths",
            _text_tuple(self.exclude_paths, "exclude_paths"),
        )
        object.__setattr__(
            self,
            "allowed_file_types",
            _text_tuple(self.allowed_file_types, "allowed_file_types"),
        )
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "profile_id": self.profile_id,
            "source": self.source.to_dict(),
            "include_paths": list(self.include_paths),
            "exclude_paths": list(self.exclude_paths),
            "allowed_file_types": list(self.allowed_file_types),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RepositoryProfile:
        source_payload = payload.get("source")
        if not isinstance(source_payload, Mapping):
            raise TypeError("source must be a mapping")
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        return cls(
            schema_version=payload.get("schema_version", ""),
            profile_id=payload.get("profile_id", ""),
            source=RepositorySource.from_dict(source_payload),
            include_paths=payload.get("include_paths", ()),
            exclude_paths=payload.get("exclude_paths", ()),
            allowed_file_types=payload.get("allowed_file_types", ()),
            metadata=metadata,
        )


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    """Stable source artifact reference with explicit content provenance."""

    schema_version: str
    artifact_id: str
    source_id: str
    source_path: str
    source_hash: str
    revision: str | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="artifact-ref",
            supported_major=1,
        )
        for field_name in ("artifact_id", "source_id", "source_path", "source_hash"):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )
        object.__setattr__(self, "revision", _optional_text(self.revision, "revision"))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "artifact_id": self.artifact_id,
            "source_id": self.source_id,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
        }
        if self.revision is not None:
            payload["revision"] = self.revision
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ArtifactRef:
        return cls(
            schema_version=payload.get("schema_version", ""),
            artifact_id=payload.get("artifact_id", ""),
            source_id=payload.get("source_id", ""),
            source_path=payload.get("source_path", ""),
            source_hash=payload.get("source_hash", ""),
            revision=payload.get("revision"),
        )
