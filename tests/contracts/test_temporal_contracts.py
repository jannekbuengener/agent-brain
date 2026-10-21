from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone

import pytest

from agent_brain.contracts.temporal import TemporalEnvelope


def test_temporal_envelope_round_trip_normalizes_to_utc_json() -> None:
    plus_two = timezone(timedelta(hours=2))
    envelope = TemporalEnvelope(
        schema_version="temporal-envelope/v1",
        known_at=datetime(2026, 10, 21, 13, 5, tzinfo=plus_two),
        valid_from=datetime(2026, 10, 1, 0, 0),
        valid_until=datetime(2026, 11, 1, 0, 0, tzinfo=UTC),
        system_as_of=datetime(2026, 10, 21, 11, 6, 7, 123456, tzinfo=UTC),
    )

    assert envelope.known_at == datetime(2026, 10, 21, 11, 5)
    assert envelope.valid_from == datetime(2026, 10, 1, 0, 0)
    assert envelope.to_dict() == {
        "schema_version": "temporal-envelope/v1",
        "known_at": "2026-10-21T11:05:00Z",
        "valid_from": "2026-10-01T00:00:00Z",
        "valid_until": "2026-11-01T00:00:00Z",
        "system_as_of": "2026-10-21T11:06:07.123456Z",
    }
    json.dumps(envelope.to_dict())
    assert TemporalEnvelope.from_dict(envelope.to_dict()) == envelope


def test_temporal_envelope_naive_datetime_is_treated_as_utc() -> None:
    envelope = TemporalEnvelope(
        schema_version="temporal-envelope/v1",
        known_at=datetime(2026, 10, 21, 11, 5),
    )

    assert envelope.to_dict()["known_at"] == "2026-10-21T11:05:00Z"


@pytest.mark.parametrize(
    ("valid_from", "valid_until"),
    [
        (datetime(2026, 10, 21, 11), datetime(2026, 10, 21, 11)),
        (datetime(2026, 10, 21, 12), datetime(2026, 10, 21, 11)),
    ],
)
def test_temporal_envelope_rejects_non_positive_validity_interval(
    valid_from: datetime,
    valid_until: datetime,
) -> None:
    with pytest.raises(ValueError, match="valid_until"):
        TemporalEnvelope(
            schema_version="temporal-envelope/v1",
            known_at=datetime(2026, 10, 21, 11),
            valid_from=valid_from,
            valid_until=valid_until,
        )


def test_temporal_envelope_ignores_unknown_additive_v1_fields() -> None:
    restored = TemporalEnvelope.from_dict(
        {
            "schema_version": "temporal-envelope/v1",
            "known_at": "2026-10-21T11:05:00Z",
            "future_optional_field": {"enabled": True},
        }
    )

    assert "future_optional_field" not in restored.to_dict()


def test_temporal_envelope_rejects_incompatible_major() -> None:
    with pytest.raises(ValueError, match="major"):
        TemporalEnvelope(
            schema_version="temporal-envelope/v2",
            known_at=datetime(2026, 10, 21, 11),
        )


def test_temporal_envelope_rejects_non_datetime_constructor_values() -> None:
    with pytest.raises(TypeError, match="known_at"):
        TemporalEnvelope(schema_version="temporal-envelope/v1", known_at="2026-10-21")  # type: ignore[arg-type]
