"""KnowledgeStore / MemoryStore port contract tests (#39)."""

from __future__ import annotations

import asyncio
import inspect
from datetime import datetime

import pytest

from agent_brain.knowledge.snapshot import BuildMetadata, KnowledgeManifest, KnowledgeSnapshot
from agent_brain.memory import (
    FORBIDDEN_WRITE_METHODS,
    KNOWLEDGE_QUERY_SCHEMA,
    MEMORY_RECALL_QUERY_SCHEMA,
    MEMORY_RECORD_SCHEMA,
    MEMORY_SCOPE_SCHEMA,
    InMemoryKnowledgeStore,
    InMemoryMemoryStore,
    InvalidMemoryScope,
    KnowledgeHit,
    KnowledgeQuery,
    KnowledgeStore,
    LookupStatus,
    MemoryRecallQuery,
    MemoryRecord,
    MemoryScope,
    MemoryScopeKind,
    MemoryStore,
    StoreAvailability,
    UnavailableKnowledgeStore,
    UnavailableMemoryStore,
    assert_read_only_store,
)


def _snapshot() -> KnowledgeSnapshot:
    return KnowledgeSnapshot(
        metadata=BuildMetadata(built_at="2026-10-21T00:00:00Z", tool_version="0.0.0"),
        manifests=(KnowledgeManifest(source_ref="src/a.py", source_hash="abc"),),
    )


def _record(*, scope: MemoryScope, record_id: str, subject_ref: str = "subj-1") -> MemoryRecord:
    return MemoryRecord(
        schema_version=MEMORY_RECORD_SCHEMA,
        record_id=record_id,
        subject_ref=subject_ref,
        scope=scope,
        content_ref=f"content:{record_id}",
        known_at=datetime(2026, 10, 21, 12, 0, 0),
        summary=f"summary {record_id}",
    )


def test_knowledge_and_memory_stores_are_protocols() -> None:
    knowledge = InMemoryKnowledgeStore(
        hits=(
            KnowledgeHit(
                record_id="k1",
                record_type="note",
                content_ref="c1",
                score=0.9,
                summary="alpha knowledge",
            ),
        ),
        snapshots={"snap-1": _snapshot()},
    )
    memory = InMemoryMemoryStore(
        records=(
            _record(
                scope=MemoryScope(
                    schema_version=MEMORY_SCOPE_SCHEMA,
                    kind=MemoryScopeKind.TENANT,
                    tenant_id="t1",
                ),
                record_id="m1",
            ),
        )
    )
    assert isinstance(knowledge, KnowledgeStore)
    assert isinstance(memory, MemoryStore)
    assert_read_only_store(knowledge)
    assert_read_only_store(memory)


def test_in_memory_knowledge_query_empty_vs_unavailable() -> None:
    async def _run() -> None:
        store = InMemoryKnowledgeStore(
            hits=(
                KnowledgeHit(
                    record_id="k1",
                    record_type="note",
                    content_ref="c1",
                    summary="alpha",
                ),
            )
        )
        empty = await store.query(
            KnowledgeQuery(
                schema_version=KNOWLEDGE_QUERY_SCHEMA,
                query_id="q1",
                text_query="zzz-no-match",
            )
        )
        assert empty.availability is StoreAvailability.AVAILABLE
        assert empty.is_empty
        assert not empty.is_unavailable

        store.mark_unavailable()
        unavailable = await store.query(
            KnowledgeQuery(
                schema_version=KNOWLEDGE_QUERY_SCHEMA,
                query_id="q2",
                text_query="alpha",
            )
        )
        assert unavailable.availability is StoreAvailability.UNAVAILABLE
        assert unavailable.is_unavailable
        assert unavailable.cardinality is None
        assert unavailable.hits == ()

    asyncio.run(_run())


def test_snapshot_lookup_ok_absent_unavailable() -> None:
    async def _run() -> None:
        store = InMemoryKnowledgeStore(snapshots={"snap-1": _snapshot()})
        ok = await store.get_snapshot("snap-1")
        assert ok.status is LookupStatus.OK
        assert ok.snapshot is not None

        absent = await store.get_snapshot("missing")
        assert absent.status is LookupStatus.ABSENT
        assert absent.snapshot is None

        store.mark_unavailable()
        unavailable = await store.get_snapshot("snap-1")
        assert unavailable.status is LookupStatus.UNAVAILABLE
        assert unavailable.snapshot is None
        assert unavailable.status is not LookupStatus.ABSENT

    asyncio.run(_run())


def test_scope_isolation_no_cross_tenant_leak() -> None:
    async def _run() -> None:
        scope_a = MemoryScope(
            schema_version=MEMORY_SCOPE_SCHEMA,
            kind=MemoryScopeKind.TENANT,
            tenant_id="tenant-a",
        )
        scope_b = MemoryScope(
            schema_version=MEMORY_SCOPE_SCHEMA,
            kind=MemoryScopeKind.TENANT,
            tenant_id="tenant-b",
        )
        store = InMemoryMemoryStore(
            records=(
                _record(scope=scope_a, record_id="a1"),
                _record(scope=scope_b, record_id="b1"),
            )
        )
        result = await store.recall(
            MemoryRecallQuery(
                schema_version=MEMORY_RECALL_QUERY_SCHEMA,
                query_id="q1",
                scope=scope_a,
            )
        )
        assert [record.record_id for record in result.records] == ["a1"]
        history = await store.history("subj-1", scope=scope_b)
        assert [record.record_id for record in history.records] == ["b1"]

    asyncio.run(_run())


def test_no_hierarchical_scope_fallback() -> None:
    async def _run() -> None:
        tenant = MemoryScope(
            schema_version=MEMORY_SCOPE_SCHEMA,
            kind=MemoryScopeKind.TENANT,
            tenant_id="t1",
        )
        agent = MemoryScope(
            schema_version=MEMORY_SCOPE_SCHEMA,
            kind=MemoryScopeKind.AGENT,
            tenant_id="t1",
            agent_id="a1",
        )
        store = InMemoryMemoryStore(records=(_record(scope=agent, record_id="agent-1"),))
        tenant_view = await store.recall(
            MemoryRecallQuery(
                schema_version=MEMORY_RECALL_QUERY_SCHEMA,
                query_id="q1",
                scope=tenant,
            )
        )
        assert tenant_view.is_empty
        assert tenant_view.availability is StoreAvailability.AVAILABLE

    asyncio.run(_run())


def test_recall_requires_explicit_scope() -> None:
    with pytest.raises(InvalidMemoryScope, match="scope is required|must be a MemoryScope"):
        MemoryRecallQuery(
            schema_version=MEMORY_RECALL_QUERY_SCHEMA,
            query_id="q1",
            scope=None,  # type: ignore[arg-type]
        )


def test_unavailable_memory_is_not_empty() -> None:
    async def _run() -> None:
        store = UnavailableMemoryStore()
        scope = MemoryScope.global_scope()
        result = await store.recall(
            MemoryRecallQuery(
                schema_version=MEMORY_RECALL_QUERY_SCHEMA,
                query_id="q1",
                scope=scope,
            )
        )
        assert result.is_unavailable
        assert not result.is_empty
        assert result.cardinality is None
        health = await store.health()
        assert health.availability is StoreAvailability.UNAVAILABLE

    asyncio.run(_run())


def test_unavailable_knowledge_adapter() -> None:
    async def _run() -> None:
        store = UnavailableKnowledgeStore()
        result = await store.query(
            KnowledgeQuery(
                schema_version=KNOWLEDGE_QUERY_SCHEMA,
                query_id="q1",
                text_query="anything",
            )
        )
        assert result.is_unavailable
        assert result.hits == ()
        lookup = await store.get_snapshot("snap-1")
        assert lookup.status is LookupStatus.UNAVAILABLE

    asyncio.run(_run())


def test_port_signatures_have_no_backend_sdk_types() -> None:
    forbidden_tokens = (
        "surreal",
        "Surreal",
        "spectron",
        "openai.agents",
        "AgentMemory",
        "SessionABC",
    )
    for protocol in (KnowledgeStore, MemoryStore):
        source = inspect.getsource(protocol)
        for token in forbidden_tokens:
            assert token not in source
        for name in FORBIDDEN_WRITE_METHODS:
            assert name not in protocol.__dict__


def test_assert_read_only_rejects_write_surface() -> None:
    class BadStore:
        async def query(self, query: KnowledgeQuery):
            raise NotImplementedError

        async def get_snapshot(self, snapshot_ref: str):
            raise NotImplementedError

        async def health(self):
            raise NotImplementedError

        async def remember(self, item: object) -> None:
            del item

    with pytest.raises(TypeError, match="remember"):
        assert_read_only_store(BadStore())
