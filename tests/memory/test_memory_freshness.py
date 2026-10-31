"""TTL / Freshness / Supersession derivation for Memory Read (#11)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from agent_brain.contracts.resolution import ResolutionState
from agent_brain.contracts.temporal import TEMPORAL_ENVELOPE_SCHEMA, TemporalEnvelope
from agent_brain.memory.errors import MemoryBoundaryError
from agent_brain.memory.read import derive_memory_resolution_state
from tests.memory.helpers_read import AS_OF, KNOWN_AT, make_entry, make_record


def test_current_within_ttl_and_validity() -> None:
    entry = make_entry(ttl_seconds=7200, valid_until=AS_OF + timedelta(hours=1))
    result = derive_memory_resolution_state(entry, as_of=AS_OF)
    assert result.resolution_state is ResolutionState.CURRENT
    assert "current" in result.reason_codes


def test_ttl_exact_boundary_is_stale() -> None:
    """as_of == known_at + ttl_seconds → STALE (inclusive expiry)."""
    ttl = 3600
    entry = make_entry(ttl_seconds=ttl, known_at=KNOWN_AT)
    exact = KNOWN_AT + timedelta(seconds=ttl)
    result = derive_memory_resolution_state(entry, as_of=exact)
    assert result.resolution_state is ResolutionState.STALE
    assert "ttl_elapsed" in result.reason_codes


def test_ttl_one_second_before_boundary_is_current() -> None:
    ttl = 3600
    entry = make_entry(ttl_seconds=ttl, known_at=KNOWN_AT)
    before = KNOWN_AT + timedelta(seconds=ttl - 1)
    result = derive_memory_resolution_state(entry, as_of=before)
    assert result.resolution_state is ResolutionState.CURRENT


def test_ttl_one_second_after_boundary_is_stale() -> None:
    ttl = 3600
    entry = make_entry(ttl_seconds=ttl, known_at=KNOWN_AT)
    after = KNOWN_AT + timedelta(seconds=ttl + 1)
    result = derive_memory_resolution_state(entry, as_of=after)
    assert result.resolution_state is ResolutionState.STALE
    assert "ttl_elapsed" in result.reason_codes


def test_valid_until_exact_boundary_is_stale() -> None:
    entry = make_entry(valid_until=AS_OF)
    result = derive_memory_resolution_state(entry, as_of=AS_OF)
    assert result.resolution_state is ResolutionState.STALE
    assert "validity_window_closed" in result.reason_codes


def test_not_yet_valid_is_unknown() -> None:
    entry = make_entry(valid_from=AS_OF + timedelta(minutes=5))
    result = derive_memory_resolution_state(entry, as_of=AS_OF)
    assert result.resolution_state is ResolutionState.UNKNOWN
    assert "not_yet_valid" in result.reason_codes


def test_not_yet_known_is_unknown() -> None:
    entry = make_entry(known_at=AS_OF + timedelta(minutes=1))
    result = derive_memory_resolution_state(entry, as_of=AS_OF)
    assert result.resolution_state is ResolutionState.UNKNOWN
    assert "not_yet_known" in result.reason_codes


def test_superseded_with_known_target() -> None:
    entry = make_entry(superseded_by_ref="mem-2")
    result = derive_memory_resolution_state(
        entry,
        as_of=AS_OF,
        known_supersession_targets={"mem-2"},
    )
    assert result.resolution_state is ResolutionState.SUPERSEDED
    assert "superseded_by_ref" in result.reason_codes


def test_broken_supersession_chain_is_unknown() -> None:
    entry = make_entry(superseded_by_ref="mem-missing")
    result = derive_memory_resolution_state(
        entry,
        as_of=AS_OF,
        known_supersession_targets={"mem-2"},
    )
    assert result.resolution_state is ResolutionState.UNKNOWN
    assert "broken_supersession_chain" in result.reason_codes


def test_superseded_dominates_ttl_stale() -> None:
    entry = make_entry(
        ttl_seconds=1,
        known_at=AS_OF - timedelta(hours=1),
        superseded_by_ref="mem-2",
    )
    result = derive_memory_resolution_state(
        entry,
        as_of=AS_OF,
        known_supersession_targets={"mem-2"},
    )
    assert result.resolution_state is ResolutionState.SUPERSEDED


def test_contradictory_valid_window_rejected_by_temporal_contract() -> None:
    with pytest.raises(ValueError, match="valid_until"):
        TemporalEnvelope(
            schema_version=TEMPORAL_ENVELOPE_SCHEMA,
            known_at=KNOWN_AT,
            valid_from=AS_OF,
            valid_until=AS_OF,
        )


def test_record_known_at_must_match_temporal() -> None:
    from agent_brain.contracts.provenance import PROVENANCE_SCHEMA, Provenance
    from agent_brain.contracts.resolution import RESOLUTION_META_SCHEMA, ResolutionMeta
    from agent_brain.memory.read.models import MEMORY_ENTRY_SCHEMA, MemoryEntry

    record = make_record(known_at=KNOWN_AT)
    with pytest.raises(MemoryBoundaryError, match="known_at"):
        MemoryEntry(
            schema_version=MEMORY_ENTRY_SCHEMA,
            record=record,
            temporal=TemporalEnvelope(
                schema_version=TEMPORAL_ENVELOPE_SCHEMA,
                known_at=KNOWN_AT + timedelta(seconds=1),
            ),
            provenance=Provenance(
                schema_version=PROVENANCE_SCHEMA,
                source_kind="repo_doc",
                source_ref="docs/START_HIER.md",
            ),
            resolution_meta=ResolutionMeta(schema_version=RESOLUTION_META_SCHEMA),
        )


def test_ttl_zero_never_expires_via_ttl() -> None:
    entry = make_entry(ttl_seconds=0, known_at=datetime(2020, 1, 1))
    result = derive_memory_resolution_state(entry, as_of=AS_OF)
    assert result.resolution_state is ResolutionState.CURRENT
