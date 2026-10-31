"""SurrealMemoryStore fail-closed tests (#10)."""

from __future__ import annotations

import asyncio

from agent_brain.memory import (
    MEMORY_RECALL_QUERY_SCHEMA,
    MEMORY_SCOPE_SCHEMA,
    MemoryRecallQuery,
    MemoryScope,
    MemoryScopeKind,
    MemoryStore,
    StoreAvailability,
    assert_read_only_store,
)
from agent_brain.surrealdb import SurrealMemoryStore
from agent_brain.surrealdb.catalog import CatalogProbe
from agent_brain.surrealdb.http import SurrealHttpProbeResult


def _ok_version(_: str, *, timeout_seconds: float) -> SurrealHttpProbeResult:
    del timeout_seconds
    return SurrealHttpProbeResult(ok=True, status_code=200, body_text="surrealdb-3.0.4")


def test_memory_store_is_read_only_protocol() -> None:
    store = SurrealMemoryStore(version_prober=_ok_version)
    assert isinstance(store, MemoryStore)
    assert_read_only_store(store)


def test_absent_namespace_recall_is_unavailable() -> None:
    def _catalog(**_kwargs: object) -> CatalogProbe:
        return CatalogProbe(
            reachable=True,
            namespaces=frozenset({"main"}),
            namespace_present=False,
            database_present=False,
            detail="configured namespace 'cdb_context_local' absent",
        )

    store = SurrealMemoryStore(version_prober=_ok_version, catalog_prober=_catalog)
    scope = MemoryScope(
        schema_version=MEMORY_SCOPE_SCHEMA,
        kind=MemoryScopeKind.TENANT,
        tenant_id="t1",
    )

    async def _run() -> None:
        result = await store.recall(
            MemoryRecallQuery(
                schema_version=MEMORY_RECALL_QUERY_SCHEMA,
                query_id="m1",
                scope=scope,
            )
        )
        assert result.availability is StoreAvailability.UNAVAILABLE
        assert result.records == ()
        assert result.detail and "cdb_context_local" in result.detail

    asyncio.run(_run())
