from __future__ import annotations

import pytest

from agent_brain.connectors.ledger import LedgerIntegrityError, normalize_ledger_events
from agent_brain.contracts import ArtifactRef
from agent_brain.core.canonical import canonical_hash


def _source() -> ArtifactRef:
    return ArtifactRef(
        schema_version="artifact-ref/v1",
        artifact_id="artifact-events",
        source_id="source-widgets",
        source_path="events/ledger.json",
        source_hash="a" * 64,
    )


def test_ledger_normalizes_order_chain_and_redacts_evidence() -> None:
    events = (
        {
            "event_id": "evt-2",
            "timestamp": "2026-01-01T00:00:02Z",
            "agent_id": "agent-a",
            "evidence": ["token=must-not-appear"],
        },
        {
            "timestamp": "2026-01-01T00:00:01Z",
            "agent_id": "agent-a",
            "message": "first",
        },
    )

    records = normalize_ledger_events(events, source=_source())

    assert [record.attributes["timestamp"] for record in records] == [
        "2026-01-01T00:00:01Z",
        "2026-01-01T00:00:02Z",
    ]
    assert records[1].attributes["prev_event_id"] == records[0].attributes["event_id"]
    assert records[0].record_type == "ledger_event"
    assert records[0].source == _source()
    assert "must-not-appear" not in str([record.to_dict() for record in records])


def test_ledger_rejects_integrity_or_signature_failure_before_output() -> None:
    mismatch = {
        "event_id": "evt-1",
        "timestamp": "2026-01-01T00:00:00Z",
        "agent_id": "agent-a",
        "event_hash": "0" * 64,
    }
    with pytest.raises(LedgerIntegrityError, match="hash_mismatch"):
        normalize_ledger_events((mismatch,), source=_source())

    blank_signature = {
        "event_id": "evt-2",
        "timestamp": "2026-01-01T00:00:00Z",
        "agent_id": "agent-a",
        "signature": " ",
    }
    with pytest.raises(LedgerIntegrityError, match="signature_invalid"):
        normalize_ledger_events((blank_signature,), source=_source())

    unsupported_signature = {
        "event_id": "evt-3",
        "timestamp": "2026-01-01T00:00:00Z",
        "agent_id": "agent-a",
        "signature": "signed",
    }
    with pytest.raises(LedgerIntegrityError, match="signature_unsupported"):
        normalize_ledger_events((unsupported_signature,), source=_source())


def test_ledger_accepts_matching_declared_hash_and_is_deterministic() -> None:
    event = {
        "event_id": "evt-1",
        "timestamp": "2026-01-01T00:00:00Z",
        "agent_id": "agent-a",
        "message": "stable",
    }
    event["event_hash"] = canonical_hash(event)

    first = normalize_ledger_events((event,), source=_source())
    second = normalize_ledger_events((event,), source=_source())

    assert first == second
