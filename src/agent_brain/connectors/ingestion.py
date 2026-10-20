"""Product-neutral contracts for deterministic local repository ingestion."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from agent_brain.contracts import (
    ArtifactRef,
    GraphEdge,
    IndexRecord,
    RepositorySource,
)
from agent_brain.core.canonical import canonical_hash

INGESTION_RESULT_SCHEMA = "repository-ingestion/v1"


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def _text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple or list of strings")
    return tuple(_required_text(value, field_name) for value in values)


@dataclass(frozen=True, slots=True)
class SensitivityRule:
    """A caller-supplied sensitivity classification for a relative path pattern."""

    path_pattern: str
    classification: str
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path_pattern", _required_text(self.path_pattern, "path_pattern"))
        object.__setattr__(self, "classification", _required_text(self.classification, "classification"))
        object.__setattr__(self, "reason", _required_text(self.reason, "reason"))

    def to_dict(self) -> dict[str, str]:
        return {
            "path_pattern": self.path_pattern,
            "classification": self.classification,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class ForbiddenRule:
    """A caller-supplied rule that excludes matching paths or contents."""

    pattern: str
    target: Literal["path", "content"]
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "pattern", _required_text(self.pattern, "pattern"))
        if self.target not in {"path", "content"}:
            raise ValueError("target must be 'path' or 'content'")
        object.__setattr__(self, "reason", _required_text(self.reason, "reason"))

    def to_dict(self) -> dict[str, str]:
        return {"pattern": self.pattern, "target": self.target, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class IngestionPolicy:
    """Generic, explicit limits and rules for a local-only ingestion run."""

    sensitivity_rules: tuple[SensitivityRule, ...] = ()
    forbidden_rules: tuple[ForbiddenRule, ...] = ()
    max_file_size_bytes: int = 1_000_000
    local_module_prefixes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.sensitivity_rules, (tuple, list)) or not all(
            isinstance(rule, SensitivityRule) for rule in self.sensitivity_rules
        ):
            raise TypeError("sensitivity_rules must contain SensitivityRule values")
        if not isinstance(self.forbidden_rules, (tuple, list)) or not all(
            isinstance(rule, ForbiddenRule) for rule in self.forbidden_rules
        ):
            raise TypeError("forbidden_rules must contain ForbiddenRule values")
        if isinstance(self.max_file_size_bytes, bool) or not isinstance(
            self.max_file_size_bytes, int
        ):
            raise TypeError("max_file_size_bytes must be a positive integer")
        if self.max_file_size_bytes <= 0:
            raise ValueError("max_file_size_bytes must be a positive integer")
        object.__setattr__(self, "sensitivity_rules", tuple(self.sensitivity_rules))
        object.__setattr__(self, "forbidden_rules", tuple(self.forbidden_rules))
        object.__setattr__(
            self,
            "local_module_prefixes",
            _text_tuple(self.local_module_prefixes, "local_module_prefixes"),
        )


@dataclass(frozen=True, slots=True)
class IngestionFinding:
    """A safe, relative-path limitation or exclusion observed during ingestion."""

    source_path: str
    status: Literal["skipped", "forbidden", "limited"]
    reason: str
    sensitivity: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path", _required_text(self.source_path, "source_path"))
        if self.status not in {"skipped", "forbidden", "limited"}:
            raise ValueError("status must be skipped, forbidden, or limited")
        object.__setattr__(self, "reason", _required_text(self.reason, "reason"))
        if self.sensitivity is not None:
            object.__setattr__(
                self,
                "sensitivity",
                _required_text(self.sensitivity, "sensitivity"),
            )

    def to_dict(self) -> dict[str, str]:
        payload: dict[str, str] = {
            "source_path": self.source_path,
            "status": self.status,
            "reason": self.reason,
        }
        if self.sensitivity is not None:
            payload["sensitivity"] = self.sensitivity
        return payload


def _ordered_payloads(items: Sequence[object], key: str) -> list[dict[str, object]]:
    payloads = [item.to_dict() for item in items]  # type: ignore[attr-defined]
    return sorted(payloads, key=lambda payload: str(payload[key]))


def build_ingestion_fingerprint(
    *,
    source: RepositorySource,
    profile_id: str,
    artifacts: Sequence[ArtifactRef],
    records: Sequence[IndexRecord],
    edges: Sequence[GraphEdge],
    findings: Sequence[IngestionFinding],
) -> str:
    """Return a deterministic fingerprint of portable ingestion outputs only."""
    if not isinstance(source, RepositorySource):
        raise TypeError("source must be a RepositorySource")
    profile_id = _required_text(profile_id, "profile_id")
    if not all(isinstance(item, ArtifactRef) for item in artifacts):
        raise TypeError("artifacts must contain ArtifactRef values")
    if not all(isinstance(item, IndexRecord) for item in records):
        raise TypeError("records must contain IndexRecord values")
    if not all(isinstance(item, GraphEdge) for item in edges):
        raise TypeError("edges must contain GraphEdge values")
    if not all(isinstance(item, IngestionFinding) for item in findings):
        raise TypeError("findings must contain IngestionFinding values")
    finding_payloads = sorted(
        (finding.to_dict() for finding in findings),
        key=lambda payload: (
            payload["source_path"],
            payload["status"],
            payload["reason"],
            payload.get("sensitivity", ""),
        ),
    )
    return canonical_hash(
        {
            "schema_version": INGESTION_RESULT_SCHEMA,
            "source": source.to_dict(),
            "profile_id": profile_id,
            "artifacts": _ordered_payloads(artifacts, "artifact_id"),
            "records": _ordered_payloads(records, "record_id"),
            "edges": _ordered_payloads(edges, "edge_id"),
            "findings": finding_payloads,
        }
    )


@dataclass(frozen=True, slots=True)
class RepositoryIngestionResult:
    """Deterministic, persist-free result consumed by the later build slice."""

    schema_version: str
    source: RepositorySource
    profile_id: str
    artifacts: tuple[ArtifactRef, ...]
    records: tuple[IndexRecord, ...]
    edges: tuple[GraphEdge, ...]
    findings: tuple[IngestionFinding, ...]
    fingerprint: str

    def __post_init__(self) -> None:
        if self.schema_version != INGESTION_RESULT_SCHEMA:
            raise ValueError(f"schema_version must be {INGESTION_RESULT_SCHEMA}")
        if not isinstance(self.source, RepositorySource):
            raise TypeError("source must be a RepositorySource")
        object.__setattr__(self, "profile_id", _required_text(self.profile_id, "profile_id"))
        if not all(isinstance(item, ArtifactRef) for item in self.artifacts):
            raise TypeError("artifacts must contain ArtifactRef values")
        if not all(isinstance(item, IndexRecord) for item in self.records):
            raise TypeError("records must contain IndexRecord values")
        if not all(isinstance(item, GraphEdge) for item in self.edges):
            raise TypeError("edges must contain GraphEdge values")
        if not all(isinstance(item, IngestionFinding) for item in self.findings):
            raise TypeError("findings must contain IngestionFinding values")
        object.__setattr__(self, "fingerprint", _required_text(self.fingerprint, "fingerprint"))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "source": self.source.to_dict(),
            "profile_id": self.profile_id,
            "artifacts": _ordered_payloads(self.artifacts, "artifact_id"),
            "records": _ordered_payloads(self.records, "record_id"),
            "edges": _ordered_payloads(self.edges, "edge_id"),
            "findings": sorted(
                (finding.to_dict() for finding in self.findings),
                key=lambda payload: (
                    payload["source_path"],
                    payload["status"],
                    payload["reason"],
                ),
            ),
            "fingerprint": self.fingerprint,
        }
