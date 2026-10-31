"""Failure-safety / fail-closed behavior for Memory Read (#11)."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from agent_brain.contracts.resolution import ResolutionState
from agent_brain.memory.in_memory import InMemoryMemoryStore
from agent_brain.memory.read import (
    ArtifactKind,
    MemoryEntryCatalog,
    MemoryReadService,
    StaticLiveStateChecker,
    classify_knowledge_result,
    classify_memory_read_result,
)
from agent_brain.memory.types import (
    KNOWLEDGE_RESULT_SCHEMA,
    KnowledgeResult,
    StoreAvailability,
)
from agent_brain.memory.unavailable import UnavailableMemoryStore
from tests.memory.helpers_read import AS_OF, make_entry, make_record, tenant_scope


def test_backend_unavailable_not_empty_success() -> None:
    entry = make_entry()
    service = MemoryReadService(
        store=UnavailableMemoryStore(),
        catalog=MemoryEntryCatalog((entry,)),
    )
    outcome = asyncio.run(
        service.recall_for_scope(tenant_scope(), as_of=AS_OF, subject_ref="subject-1")
    )
    assert outcome.availability is StoreAvailability.UNAVAILABLE
    assert outcome.items == ()
    assert outcome.is_unavailable is True
    assert "backend_unavailable" in outcome.limitations


def test_empty_result_is_empty_not_unavailable() -> None:
    service = MemoryReadService(
        store=InMemoryMemoryStore(records=()),
        catalog=MemoryEntryCatalog(),
    )
    outcome = asyncio.run(
        service.recall_for_scope(tenant_scope(), as_of=AS_OF, subject_ref="subject-1")
    )
    assert outcome.availability is StoreAvailability.AVAILABLE
    assert outcome.items == ()
    assert outcome.admissible_items == ()


def test_missing_catalog_metadata_unknown_not_trusted() -> None:
    record = make_record(record_id="orphan")
    service = MemoryReadService(
        store=InMemoryMemoryStore(records=(record,)),
        catalog=MemoryEntryCatalog(),
    )
    outcome = asyncio.run(
        service.recall_for_scope(tenant_scope(), as_of=AS_OF, subject_ref="subject-1")
    )
    assert len(outcome.items) == 1
    item = outcome.items[0]
    assert item.resolution_state is ResolutionState.UNKNOWN
    assert item.admissible_as_context is False
    assert "missing_entry_metadata" in item.reason_codes


def test_missing_provenance_evidence_not_admissible() -> None:
    entry = make_entry(evidence_refs=())
    service = MemoryReadService(
        store=InMemoryMemoryStore(records=(entry.record,)),
        catalog=MemoryEntryCatalog((entry,)),
    )
    outcome = asyncio.run(
        service.recall_for_scope(tenant_scope(), as_of=AS_OF, subject_ref="subject-1")
    )
    item = outcome.items[0]
    assert item.resolution_state is ResolutionState.UNKNOWN
    assert item.admissible_as_context is False
    assert "missing_evidence_or_lineage" in item.reason_codes


def test_superseded_not_delete_still_visible() -> None:
    older = make_entry(record_id="mem-old", superseded_by_ref="mem-new")
    newer = make_entry(record_id="mem-new")
    store = InMemoryMemoryStore(records=(older.record, newer.record))
    service = MemoryReadService(
        store=store,
        catalog=MemoryEntryCatalog((older, newer)),
    )
    outcome = asyncio.run(
        service.recall_for_scope(tenant_scope(), as_of=AS_OF, subject_ref="subject-1")
    )
    by_id = {item.entry.record.record_id: item for item in outcome.items}
    assert "mem-old" in by_id
    assert by_id["mem-old"].resolution_state is ResolutionState.SUPERSEDED
    assert by_id["mem-old"].admissible_as_context is False
    assert by_id["mem-new"].admissible_as_context is True


def test_ttl_expired_stale_not_false() -> None:
    entry = make_entry(ttl_seconds=60, known_at=AS_OF - timedelta(hours=2))
    service = MemoryReadService(
        store=InMemoryMemoryStore(records=(entry.record,)),
        catalog=MemoryEntryCatalog((entry,)),
    )
    outcome = asyncio.run(
        service.recall_for_scope(tenant_scope(), as_of=AS_OF, subject_ref="subject-1")
    )
    item = outcome.items[0]
    assert item.resolution_state is ResolutionState.STALE
    assert item.admissible_as_context is False


def test_knowledge_and_memory_kinds_remain_distinct() -> None:
    entry = make_entry()
    service = MemoryReadService(
        store=InMemoryMemoryStore(records=(entry.record,)),
        catalog=MemoryEntryCatalog((entry,)),
    )
    memory_result = asyncio.run(
        service.recall_for_scope(tenant_scope(), as_of=AS_OF, subject_ref="subject-1")
    )
    knowledge_result = KnowledgeResult(
        schema_version=KNOWLEDGE_RESULT_SCHEMA,
        availability=StoreAvailability.AVAILABLE,
        hits=(),
    )
    assert classify_memory_read_result(memory_result) is ArtifactKind.MEMORY
    assert classify_knowledge_result(knowledge_result) is ArtifactKind.KNOWLEDGE_BUILD
    assert memory_result.artifact_kind is ArtifactKind.MEMORY


def test_no_write_surface_on_read_service_store() -> None:
    from agent_brain.memory.ports import FORBIDDEN_WRITE_METHODS, assert_read_only_store

    store = InMemoryMemoryStore()
    assert_read_only_store(store)
    for name in FORBIDDEN_WRITE_METHODS:
        assert not callable(getattr(MemoryReadService, name, None))


def test_live_checker_returns_none_fail_closed() -> None:
    from agent_brain.memory.read.models import LIVE_CLAIM_SCHEMA, LiveStateClaim

    entry = make_entry(
        live_claim=LiveStateClaim(
            schema_version=LIVE_CLAIM_SCHEMA,
            claim_key="issue:11:state",
            asserted_value="open",
        )
    )
    service = MemoryReadService(
        store=InMemoryMemoryStore(records=(entry.record,)),
        catalog=MemoryEntryCatalog((entry,)),
        live_checker=StaticLiveStateChecker({"issue:11:state": None}),
    )
    outcome = asyncio.run(
        service.recall_for_scope(tenant_scope(), as_of=AS_OF, subject_ref="subject-1")
    )
    item = outcome.items[0]
    assert item.admissible_as_context is False
    assert item.resolution_state is ResolutionState.UNKNOWN
