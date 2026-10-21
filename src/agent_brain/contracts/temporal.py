"""Backend-neutral tri-temporal metadata contract."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agent_brain.contracts._validation import (
    format_utc_datetime,
    normalize_utc_datetime,
    parse_optional_utc_datetime,
    parse_utc_datetime,
)
from agent_brain.contracts.versioning import require_compatible_version

TEMPORAL_ENVELOPE_SCHEMA = "temporal-envelope/v1"


@dataclass(frozen=True, slots=True)
class TemporalEnvelope:
    """Known/valid time plus optional storage snapshot metadata.

    Datetimes are normalized to naive UTC internally. ``system_as_of`` is
    read/storage metadata; it is not real-world validity and carries no
    resolver authority by itself.
    """

    schema_version: str
    known_at: datetime
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    system_as_of: datetime | None = None

    def __post_init__(self) -> None:
        require_compatible_version(
            self.schema_version,
            expected_family="temporal-envelope",
            supported_major=1,
        )
        object.__setattr__(
            self,
            "known_at",
            normalize_utc_datetime(self.known_at, "known_at"),
        )
        for field_name in ("valid_from", "valid_until", "system_as_of"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    normalize_utc_datetime(value, field_name),
                )
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_until <= self.valid_from
        ):
            raise ValueError("valid_until must be strictly after valid_from")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "known_at": format_utc_datetime(self.known_at),
        }
        for field_name in ("valid_from", "valid_until", "system_as_of"):
            value = getattr(self, field_name)
            if value is not None:
                payload[field_name] = format_utc_datetime(value)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TemporalEnvelope:
        return cls(
            schema_version=payload.get("schema_version", ""),
            known_at=parse_utc_datetime(payload.get("known_at"), "known_at"),
            valid_from=parse_optional_utc_datetime(payload.get("valid_from"), "valid_from"),
            valid_until=parse_optional_utc_datetime(payload.get("valid_until"), "valid_until"),
            system_as_of=parse_optional_utc_datetime(
                payload.get("system_as_of"),
                "system_as_of",
            ),
        )
