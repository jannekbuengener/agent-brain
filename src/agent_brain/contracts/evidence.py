"""Product-neutral evidence and claim reference contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from agent_brain.contracts.versioning import require_compatible_version

EVIDENCE_REF_SCHEMA = "evidence-ref/v1"
CLAIM_REF_SCHEMA = "claim-ref/v1"


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


def _text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        raise TypeError(f"{field_name} must be a list or tuple of strings")
    return tuple(_required_text(item, field_name) for item in values)


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    """Reference-only evidence record without trust or resolver authority."""

    schema_version: str
    evidence_id: str
    evidence_type: str
    source_refs: tuple[str, ...] = ()
    artifact_refs: tuple[str, ...] = ()
    claim_refs: tuple[str, ...] = ()
    decision_refs: tuple[str, ...] = ()
    content_hash: str | None = None
    summary: str | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="evidence-ref",
            supported_major=1,
        )
        object.__setattr__(
            self,
            "evidence_id",
            _required_text(self.evidence_id, "evidence_id"),
        )
        object.__setattr__(
            self,
            "evidence_type",
            _required_text(self.evidence_type, "evidence_type"),
        )
        for field_name in ("source_refs", "artifact_refs", "claim_refs", "decision_refs"):
            object.__setattr__(
                self,
                field_name,
                _text_tuple(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "content_hash",
            _optional_text(self.content_hash, "content_hash"),
        )
        object.__setattr__(self, "summary", _optional_text(self.summary, "summary"))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "source_refs": list(self.source_refs),
            "artifact_refs": list(self.artifact_refs),
            "claim_refs": list(self.claim_refs),
            "decision_refs": list(self.decision_refs),
        }
        if self.content_hash is not None:
            payload["content_hash"] = self.content_hash
        if self.summary is not None:
            payload["summary"] = self.summary
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> EvidenceRef:
        return cls(
            schema_version=payload.get("schema_version", ""),
            evidence_id=payload.get("evidence_id", ""),
            evidence_type=payload.get("evidence_type", ""),
            source_refs=_text_tuple(payload.get("source_refs", ()), "source_refs"),
            artifact_refs=_text_tuple(payload.get("artifact_refs", ()), "artifact_refs"),
            claim_refs=_text_tuple(payload.get("claim_refs", ()), "claim_refs"),
            decision_refs=_text_tuple(payload.get("decision_refs", ()), "decision_refs"),
            content_hash=payload.get("content_hash"),
            summary=payload.get("summary"),
        )


@dataclass(frozen=True, slots=True)
class ClaimRef:
    """Reference-only claim record whose resolution belongs to a later slice."""

    schema_version: str
    claim_id: str
    claim_type: str
    statement: str | None = None
    evidence_refs: tuple[str, ...] = ()
    artifact_refs: tuple[str, ...] = ()
    decision_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="claim-ref",
            supported_major=1,
        )
        object.__setattr__(self, "claim_id", _required_text(self.claim_id, "claim_id"))
        object.__setattr__(
            self,
            "claim_type",
            _required_text(self.claim_type, "claim_type"),
        )
        object.__setattr__(
            self,
            "statement",
            _optional_text(self.statement, "statement"),
        )
        for field_name in ("evidence_refs", "artifact_refs", "decision_refs", "source_refs"):
            object.__setattr__(
                self,
                field_name,
                _text_tuple(getattr(self, field_name), field_name),
            )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "claim_id": self.claim_id,
            "claim_type": self.claim_type,
            "evidence_refs": list(self.evidence_refs),
            "artifact_refs": list(self.artifact_refs),
            "decision_refs": list(self.decision_refs),
            "source_refs": list(self.source_refs),
        }
        if self.statement is not None:
            payload["statement"] = self.statement
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ClaimRef:
        return cls(
            schema_version=payload.get("schema_version", ""),
            claim_id=payload.get("claim_id", ""),
            claim_type=payload.get("claim_type", ""),
            statement=payload.get("statement"),
            evidence_refs=_text_tuple(payload.get("evidence_refs", ()), "evidence_refs"),
            artifact_refs=_text_tuple(payload.get("artifact_refs", ()), "artifact_refs"),
            decision_refs=_text_tuple(payload.get("decision_refs", ()), "decision_refs"),
            source_refs=_text_tuple(payload.get("source_refs", ()), "source_refs"),
        )
