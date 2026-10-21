"""Structured, backend-neutral provenance metadata contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agent_brain.contracts._validation import (
    format_utc_datetime,
    normalize_utc_datetime,
    optional_text,
    parse_optional_utc_datetime,
    required_text,
    text_tuple,
)
from agent_brain.contracts.versioning import require_compatible_version

PROVENANCE_SCHEMA = "provenance/v1"


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """Zero-based, end-exclusive Unicode-codepoint source span."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if isinstance(self.start, bool) or not isinstance(self.start, int):
            raise TypeError("start must be an integer")
        if isinstance(self.end, bool) or not isinstance(self.end, int):
            raise TypeError("end must be an integer")
        if self.start < 0:
            raise ValueError("start must be >= 0")
        if self.end <= self.start:
            raise ValueError("end must be strictly greater than start")

    def to_dict(self) -> dict[str, int]:
        return {"start": self.start, "end": self.end}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SourceSpan:
        if not isinstance(payload, Mapping):
            raise TypeError("source_span must be a mapping")
        return cls(start=payload.get("start"), end=payload.get("end"))


@dataclass(frozen=True, slots=True)
class Provenance:
    """Structured origin and lineage without resolver or trust authority."""

    schema_version: str
    source_kind: str
    source_ref: str
    source_hash: str | None = None
    source_span: SourceSpan | None = None
    source_session_id: str | None = None
    source_turn_at: datetime | None = None
    derived_from: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="provenance",
            supported_major=1,
        )
        object.__setattr__(self, "source_kind", required_text(self.source_kind, "source_kind"))
        object.__setattr__(self, "source_ref", required_text(self.source_ref, "source_ref"))
        object.__setattr__(self, "source_hash", optional_text(self.source_hash, "source_hash"))
        if self.source_span is not None and not isinstance(self.source_span, SourceSpan):
            raise TypeError("source_span must be a SourceSpan")
        object.__setattr__(
            self,
            "source_session_id",
            optional_text(self.source_session_id, "source_session_id"),
        )
        if self.source_turn_at is not None:
            object.__setattr__(
                self,
                "source_turn_at",
                normalize_utc_datetime(self.source_turn_at, "source_turn_at"),
            )
        object.__setattr__(
            self,
            "derived_from",
            text_tuple(self.derived_from, "derived_from"),
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "source_kind": self.source_kind,
            "source_ref": self.source_ref,
            "derived_from": list(self.derived_from),
        }
        if self.source_hash is not None:
            payload["source_hash"] = self.source_hash
        if self.source_span is not None:
            payload["source_span"] = self.source_span.to_dict()
        if self.source_session_id is not None:
            payload["source_session_id"] = self.source_session_id
        if self.source_turn_at is not None:
            payload["source_turn_at"] = format_utc_datetime(self.source_turn_at)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Provenance:
        raw_span = payload.get("source_span")
        return cls(
            schema_version=payload.get("schema_version", ""),
            source_kind=payload.get("source_kind", ""),
            source_ref=payload.get("source_ref", ""),
            source_hash=payload.get("source_hash"),
            source_span=None if raw_span is None else SourceSpan.from_dict(raw_span),
            source_session_id=payload.get("source_session_id"),
            source_turn_at=parse_optional_utc_datetime(
                payload.get("source_turn_at"),
                "source_turn_at",
            ),
            derived_from=text_tuple(payload.get("derived_from", ()), "derived_from"),
        )
