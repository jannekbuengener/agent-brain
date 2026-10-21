from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from agent_brain.contracts.provenance import Provenance, SourceSpan


def test_source_span_is_zero_based_end_exclusive_value_type() -> None:
    span = SourceSpan(start=0, end=5)
    assert span.to_dict() == {"start": 0, "end": 5}
    assert SourceSpan.from_dict(span.to_dict()) == span


@pytest.mark.parametrize(("start", "end"), [(-1, 1), (0, 0), (3, 2), (True, 2), (0, False)])
def test_source_span_rejects_invalid_offsets(start, end) -> None:
    error = (TypeError, ValueError)
    with pytest.raises(error):
        SourceSpan(start=start, end=end)


def test_provenance_round_trip_is_json_safe_and_normalizes_turn_time() -> None:
    plus_two = timezone(timedelta(hours=2))
    provenance = Provenance(
        schema_version="provenance/v1",
        source_kind=" repo ",
        source_ref=" github:example/repo@abc ",
        source_hash="a" * 64,
        source_span=SourceSpan(start=7, end=11),
        source_session_id=" session-7 ",
        source_turn_at=datetime(2026, 10, 21, 13, 5, tzinfo=plus_two),
        derived_from=("evidence:a", "claim:b"),
    )

    assert provenance.source_kind == "repo"
    assert provenance.source_ref == "github:example/repo@abc"
    assert provenance.source_turn_at == datetime(2026, 10, 21, 11, 5)
    assert provenance.to_dict() == {
        "schema_version": "provenance/v1",
        "source_kind": "repo",
        "source_ref": "github:example/repo@abc",
        "source_hash": "a" * 64,
        "source_span": {"start": 7, "end": 11},
        "source_session_id": "session-7",
        "source_turn_at": "2026-10-21T11:05:00Z",
        "derived_from": ["evidence:a", "claim:b"],
    }
    json.dumps(provenance.to_dict())
    assert Provenance.from_dict(provenance.to_dict()) == provenance


def test_provenance_ignores_unknown_additive_v1_fields() -> None:
    restored = Provenance.from_dict(
        {
            "schema_version": "provenance/v1",
            "source_kind": "document",
            "source_ref": "docs/spec.md",
            "derived_from": [],
            "future_optional_field": True,
        }
    )
    assert "future_optional_field" not in restored.to_dict()


def test_provenance_rejects_blank_required_text() -> None:
    with pytest.raises(ValueError, match="source_ref"):
        Provenance(
            schema_version="provenance/v1",
            source_kind="repo",
            source_ref=" ",
        )


def test_provenance_rejects_incompatible_major() -> None:
    with pytest.raises(ValueError, match="major"):
        Provenance(
            schema_version="provenance/v2",
            source_kind="repo",
            source_ref="repo:example",
        )

