"""Supersession and trust/confidence metadata without resolver authority."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from agent_brain.contracts._validation import optional_text, optional_unit_interval
from agent_brain.contracts.versioning import require_compatible_version

RESOLUTION_META_SCHEMA = "resolution-meta/v1"


class ResolutionState(StrEnum):
    """Read-side states derived later by resolver/freshness logic."""

    CURRENT = "CURRENT"
    STALE = "STALE"
    SUPERSEDED = "SUPERSEDED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ResolutionMeta:
    """Supersession links and independent trust/confidence metadata."""

    schema_version: str
    supersedes_ref: str | None = None
    superseded_by_ref: str | None = None
    supersession_reason: str | None = None
    source_trust: float | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="resolution-meta",
            supported_major=1,
        )
        for field_name in ("supersedes_ref", "superseded_by_ref", "supersession_reason"):
            object.__setattr__(
                self,
                field_name,
                optional_text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "source_trust",
            optional_unit_interval(self.source_trust, "source_trust"),
        )
        object.__setattr__(
            self,
            "confidence",
            optional_unit_interval(self.confidence, "confidence"),
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"schema_version": self.schema_version}
        for field_name in (
            "supersedes_ref",
            "superseded_by_ref",
            "supersession_reason",
            "source_trust",
            "confidence",
        ):
            value = getattr(self, field_name)
            if value is not None:
                payload[field_name] = value
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ResolutionMeta:
        return cls(
            schema_version=payload.get("schema_version", ""),
            supersedes_ref=payload.get("supersedes_ref"),
            superseded_by_ref=payload.get("superseded_by_ref"),
            supersession_reason=payload.get("supersession_reason"),
            source_trust=payload.get("source_trust"),
            confidence=payload.get("confidence"),
        )
