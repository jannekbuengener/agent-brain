"""Live-State revalidation for Memory Read (#11)."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from agent_brain.contracts.resolution import ResolutionState
from agent_brain.core.source_priority import SourcePriority
from agent_brain.memory.in_memory import InMemoryMemoryStore
from agent_brain.memory.read import (
    LiveStateObservation,
    MemoryEntryCatalog,
    MemoryReadService,
    StaticLiveStateChecker,
    revalidate_against_live_state,
)
from agent_brain.memory.read.models import LiveRevalidationStatus
from tests.memory.helpers_read import (
    AS_OF,
    issue_open_claim,
    make_entry,
    tenant_scope,
)


def test_live_contradiction_memory_does_not_win() -> None:
    entry = make_entry(live_claim=issue_open_claim())
    checker = StaticLiveStateChecker(
        {
            "issue:11:state": LiveStateObservation(
                claim_key="issue:11:state",
                value="closed",
                source="github_live",
            )
        }
    )
    result = revalidate_against_live_state(entry, checker=checker)
    assert result.status is LiveRevalidationStatus.CONTRADICTED
    assert result.observed_value == "closed"
    assert result.observed_source == "github_live"


def test_live_unavailable_does_not_confirm_memory() -> None:
    entry = make_entry(live_claim=issue_open_claim())
    result = revalidate_against_live_state(entry, checker=None)
    assert result.status is LiveRevalidationStatus.UNAVAILABLE
    assert result.reason_code == "live_checker_absent"


def test_live_match_confirmed() -> None:
    entry = make_entry(live_claim=issue_open_claim())
    checker = StaticLiveStateChecker(
        {
            "issue:11:state": LiveStateObservation(
                claim_key="issue:11:state",
                value="open",
                source="github_live",
            )
        }
    )
    result = revalidate_against_live_state(entry, checker=checker)
    assert result.status is LiveRevalidationStatus.CONFIRMED


def test_service_marks_contradicted_memory_stale_not_admissible() -> None:
    entry = make_entry(live_claim=issue_open_claim())
    store = InMemoryMemoryStore(records=(entry.record,))
    catalog = MemoryEntryCatalog((entry,))
    checker = StaticLiveStateChecker(
        {
            "issue:11:state": LiveStateObservation(
                claim_key="issue:11:state",
                value="closed",
                source="github_live",
            )
        }
    )
    service = MemoryReadService(store=store, catalog=catalog, live_checker=checker)
    outcome = asyncio.run(
        service.recall_for_scope(tenant_scope(), as_of=AS_OF, subject_ref="subject-1")
    )
    assert len(outcome.items) == 1
    item = outcome.items[0]
    assert item.resolution_state is ResolutionState.STALE
    assert item.admissible_as_context is False
    assert "live_contradicts_memory" in item.reason_codes


def test_service_required_live_unavailable_is_unknown_not_current() -> None:
    entry = make_entry(live_claim=issue_open_claim(), ttl_seconds=10_000)
    store = InMemoryMemoryStore(records=(entry.record,))
    catalog = MemoryEntryCatalog((entry,))
    service = MemoryReadService(store=store, catalog=catalog, live_checker=None)
    outcome = asyncio.run(
        service.recall_for_scope(tenant_scope(), as_of=AS_OF, subject_ref="subject-1")
    )
    item = outcome.items[0]
    assert item.resolution_state is ResolutionState.UNKNOWN
    assert item.admissible_as_context is False
    assert "live_checker_absent" in item.reason_codes or (
        "live_check_unavailable" in item.reason_codes
    )


def test_repo_live_outranks_memory_via_source_priority() -> None:
    entry = make_entry(live_claim=issue_open_claim())
    checker = StaticLiveStateChecker(
        {
            "issue:11:state": LiveStateObservation(
                claim_key="issue:11:state",
                value="closed",
                source="repo_live",
            )
        }
    )
    priority = SourcePriority(
        ordered_sources=("github_live", "repo_live", "verified_evidence", "memory")
    )
    result = revalidate_against_live_state(
        entry, checker=checker, source_priority=priority
    )
    assert result.status is LiveRevalidationStatus.CONTRADICTED


def test_current_without_live_claim_remains_admissible() -> None:
    entry = make_entry(ttl_seconds=7200, live_claim=None)
    store = InMemoryMemoryStore(records=(entry.record,))
    service = MemoryReadService(
        store=store,
        catalog=MemoryEntryCatalog((entry,)),
        live_checker=None,
    )
    outcome = asyncio.run(
        service.recall_for_scope(tenant_scope(), as_of=AS_OF, subject_ref="subject-1")
    )
    item = outcome.items[0]
    assert item.resolution_state is ResolutionState.CURRENT
    assert item.admissible_as_context is True
    assert item.live_revalidation is not None
    assert item.live_revalidation.status is LiveRevalidationStatus.NOT_APPLICABLE


def test_stale_ttl_not_false_still_returned() -> None:
    entry = make_entry(ttl_seconds=1, known_at=AS_OF - timedelta(hours=1))
    store = InMemoryMemoryStore(records=(entry.record,))
    service = MemoryReadService(
        store=store,
        catalog=MemoryEntryCatalog((entry,)),
    )
    outcome = asyncio.run(
        service.recall_for_scope(tenant_scope(), as_of=AS_OF, subject_ref="subject-1")
    )
    item = outcome.items[0]
    assert item.resolution_state is ResolutionState.STALE
    assert item.admissible_as_context is False
    assert len(outcome.items) == 1  # STALE != filtered/deleted
