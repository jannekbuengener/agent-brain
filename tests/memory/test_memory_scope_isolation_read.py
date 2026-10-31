"""Scope isolation for Memory Read path (#11)."""

from __future__ import annotations

import asyncio

import pytest

from agent_brain.memory import InvalidMemoryScope, MemoryRecallQuery, MemoryScope
from agent_brain.memory.in_memory import InMemoryMemoryStore
from agent_brain.memory.read import MemoryEntryCatalog, MemoryReadService
from agent_brain.memory.types import MEMORY_RECALL_QUERY_SCHEMA
from tests.memory.helpers_read import (
    AS_OF,
    make_entry,
    session_scope,
    tenant_scope,
)


def test_same_user_different_tenant_no_leakage() -> None:
    a = make_entry(record_id="mem-a", scope=tenant_scope("tenant-a"))
    b = make_entry(record_id="mem-b", scope=tenant_scope("tenant-b"))
    store = InMemoryMemoryStore(records=(a.record, b.record))
    service = MemoryReadService(
        store=store,
        catalog=MemoryEntryCatalog((a, b)),
    )
    outcome = asyncio.run(
        service.recall_for_scope(
            tenant_scope("tenant-a"),
            as_of=AS_OF,
            subject_ref="subject-1",
        )
    )
    ids = {item.entry.record.record_id for item in outcome.items}
    assert ids == {"mem-a"}
    assert "mem-b" not in ids


def test_same_tenant_different_session_no_leakage() -> None:
    s1 = make_entry(
        record_id="mem-s1",
        scope=session_scope(session_id="session-1"),
    )
    s2 = make_entry(
        record_id="mem-s2",
        scope=session_scope(session_id="session-2"),
    )
    store = InMemoryMemoryStore(records=(s1.record, s2.record))
    service = MemoryReadService(
        store=store,
        catalog=MemoryEntryCatalog((s1, s2)),
    )
    outcome = asyncio.run(
        service.recall_for_scope(
            session_scope(session_id="session-1"),
            as_of=AS_OF,
            subject_ref="subject-1",
        )
    )
    ids = {item.entry.record.record_id for item in outcome.items}
    assert ids == {"mem-s1"}


def test_missing_scope_rejected() -> None:
    with pytest.raises(InvalidMemoryScope):
        MemoryRecallQuery(
            schema_version=MEMORY_RECALL_QUERY_SCHEMA,
            query_id="q1",
            scope=None,  # type: ignore[arg-type]
        )


def test_invalid_scope_rejected() -> None:
    with pytest.raises(InvalidMemoryScope):
        MemoryScope.from_dict({"schema_version": "memory-scope/v1"})


def test_narrow_vs_broad_scope_exact_match_only() -> None:
    """Exact match semantics: tenant scope does not see session-scoped rows."""
    tenant = make_entry(record_id="mem-tenant", scope=tenant_scope("tenant-a"))
    session = make_entry(
        record_id="mem-session",
        scope=session_scope(tenant_id="tenant-a", session_id="session-1"),
    )
    store = InMemoryMemoryStore(records=(tenant.record, session.record))
    service = MemoryReadService(
        store=store,
        catalog=MemoryEntryCatalog((tenant, session)),
    )
    tenant_out = asyncio.run(
        service.recall_for_scope(
            tenant_scope("tenant-a"),
            as_of=AS_OF,
            subject_ref="subject-1",
        )
    )
    session_out = asyncio.run(
        service.recall_for_scope(
            session_scope(tenant_id="tenant-a", session_id="session-1"),
            as_of=AS_OF,
            subject_ref="subject-1",
        )
    )
    assert {i.entry.record.record_id for i in tenant_out.items} == {"mem-tenant"}
    assert {i.entry.record.record_id for i in session_out.items} == {"mem-session"}
