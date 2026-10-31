"""Goal #67 coordinated delivery bundle tests."""

from __future__ import annotations

import asyncio

from agent_brain.memory import (
    FORBIDDEN_WRITE_METHODS,
    KNOWLEDGE_QUERY_SCHEMA,
    MEMORY_RECALL_QUERY_SCHEMA,
    MEMORY_SCOPE_SCHEMA,
    KnowledgeQuery,
    MemoryRecallQuery,
    MemoryScope,
    MemoryScopeKind,
    StoreAvailability,
    assert_read_only_store,
)
from agent_brain.surrealdb import (
    HandoffOutcome,
    build_read_handoff_bundle,
)


def test_bundle_shares_truth_backed_settings_and_handoff_go() -> None:
    bundle = build_read_handoff_bundle()
    assert bundle.handoff.outcome is HandoffOutcome.STATE_HANDOFF_GO
    assert bundle.exit_token_ready
    assert bundle.knowledge.settings is bundle.settings
    assert bundle.memory.settings is bundle.settings
    assert bundle.settings.namespace == "cdb_context_local"
    assert bundle.settings.expected_server_version_prefix == "surrealdb-3.0"
    assert_read_only_store(bundle.knowledge)
    assert_read_only_store(bundle.memory)
    for name in FORBIDDEN_WRITE_METHODS:
        assert not callable(getattr(bundle.knowledge, name, None))
        assert not callable(getattr(bundle.memory, name, None))


def test_bundle_stores_fail_closed_when_endpoint_offline() -> None:
    bundle = build_read_handoff_bundle()
    scope = MemoryScope(
        schema_version=MEMORY_SCOPE_SCHEMA,
        kind=MemoryScopeKind.TENANT,
        tenant_id="t1",
    )

    async def _run() -> None:
        knowledge = await bundle.knowledge.query(
            KnowledgeQuery(
                schema_version=KNOWLEDGE_QUERY_SCHEMA,
                query_id="g67",
                text_query="x",
            )
        )
        memory = await bundle.memory.recall(
            MemoryRecallQuery(
                schema_version=MEMORY_RECALL_QUERY_SCHEMA,
                query_id="g67m",
                scope=scope,
            )
        )
        assert knowledge.availability is StoreAvailability.UNAVAILABLE
        assert memory.availability is StoreAvailability.UNAVAILABLE

    asyncio.run(_run())
