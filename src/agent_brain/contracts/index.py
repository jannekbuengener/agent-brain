"""Minimal product-neutral index and graph record contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from agent_brain.contracts.repository import ArtifactRef
from agent_brain.contracts.versioning import require_compatible_version
from agent_brain.core.canonical import canonical_hash

INDEX_RECORD_SCHEMA = "index-record/v1"
GRAPH_EDGE_SCHEMA = "graph-edge/v1"


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


@dataclass(frozen=True, slots=True)
class IndexRecord:
    """Smallest shared index record consumed by later reasoning slices."""

    schema_version: str
    record_id: str
    record_type: str
    source: ArtifactRef
    content_hash: str | None = None
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="index-record",
            supported_major=1,
        )
        object.__setattr__(self, "record_id", _required_text(self.record_id, "record_id"))
        object.__setattr__(
            self,
            "record_type",
            _required_text(self.record_type, "record_type"),
        )
        if not isinstance(self.source, ArtifactRef):
            raise TypeError("source must be an ArtifactRef")
        object.__setattr__(
            self,
            "content_hash",
            _optional_text(self.content_hash, "content_hash"),
        )
        if not isinstance(self.attributes, Mapping):
            raise TypeError("attributes must be a mapping")
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "record_id": self.record_id,
            "record_type": self.record_type,
            "source": self.source.to_dict(),
        }
        if self.content_hash is not None:
            payload["content_hash"] = self.content_hash
        payload["attributes"] = dict(self.attributes)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> IndexRecord:
        source_payload = payload.get("source")
        if not isinstance(source_payload, Mapping):
            raise TypeError("source must be a mapping")
        attributes = payload.get("attributes", {})
        if not isinstance(attributes, Mapping):
            raise TypeError("attributes must be a mapping")
        return cls(
            schema_version=str(payload.get("schema_version", "")),
            record_id=str(payload.get("record_id", "")),
            record_type=str(payload.get("record_type", "")),
            source=ArtifactRef.from_dict(source_payload),
            content_hash=payload.get("content_hash"),
            attributes=attributes,
        )


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """Directed structural relation between two opaque index record IDs."""

    schema_version: str
    edge_id: str
    from_id: str
    to_id: str
    edge_type: str
    source: ArtifactRef | None = None
    confidence: float = 1.0
    inferred: bool = False

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="graph-edge",
            supported_major=1,
        )
        for field_name in ("edge_id", "from_id", "to_id", "edge_type"):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )
        if self.source is not None and not isinstance(self.source, ArtifactRef):
            raise TypeError("source must be an ArtifactRef when present")
        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise TypeError("confidence must be a number")
        normalized_confidence = float(self.confidence)
        if not 0.0 <= normalized_confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        object.__setattr__(self, "confidence", normalized_confidence)
        if not isinstance(self.inferred, bool):
            raise TypeError("inferred must be a bool")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "edge_id": self.edge_id,
            "from_id": self.from_id,
            "to_id": self.to_id,
            "edge_type": self.edge_type,
            "confidence": self.confidence,
            "inferred": self.inferred,
        }
        if self.source is not None:
            payload["source"] = self.source.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> GraphEdge:
        source_payload = payload.get("source")
        source: ArtifactRef | None = None
        if source_payload is not None:
            if not isinstance(source_payload, Mapping):
                raise TypeError("source must be a mapping when present")
            source = ArtifactRef.from_dict(source_payload)
        return cls(
            schema_version=str(payload.get("schema_version", "")),
            edge_id=str(payload.get("edge_id", "")),
            from_id=str(payload.get("from_id", "")),
            to_id=str(payload.get("to_id", "")),
            edge_type=str(payload.get("edge_type", "")),
            source=source,
            confidence=payload.get("confidence", 1.0),
            inferred=payload.get("inferred", False),
        )


def graph_fingerprint(
    records: Sequence[IndexRecord],
    edges: Sequence[GraphEdge],
) -> str:
    """Return a deterministic structural fingerprint independent of input order."""
    record_payloads = sorted(
        (record.to_dict() for record in records),
        key=lambda item: str(item["record_id"]),
    )
    edge_payloads = sorted(
        (edge.to_dict() for edge in edges),
        key=lambda item: str(item["edge_id"]),
    )
    return canonical_hash({"records": record_payloads, "edges": edge_payloads})
