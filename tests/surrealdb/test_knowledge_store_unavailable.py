"""SurrealKnowledgeStore fail-closed behaviour (#10)."""

from __future__ import annotations

import asyncio

from agent_brain.memory import (
    KNOWLEDGE_QUERY_SCHEMA,
    KnowledgeQuery,
    KnowledgeStore,
    LookupStatus,
    StoreAvailability,
    assert_read_only_store,
)
from agent_brain.surrealdb import SurrealDbReadSettings, SurrealKnowledgeStore
from agent_brain.surrealdb.catalog import CatalogProbe
from agent_brain.surrealdb.http import SurrealHttpProbeResult


def _ok_version(_: str, *, timeout_seconds: float) -> SurrealHttpProbeResult:
    del timeout_seconds
    return SurrealHttpProbeResult(ok=True, status_code=200, body_text="surrealdb-3.0.4")


def _down_version(_: str, *, timeout_seconds: float) -> SurrealHttpProbeResult:
    del timeout_seconds
    return SurrealHttpProbeResult(ok=False, error="URLError: connection refused")


def test_surreal_knowledge_store_is_read_only_protocol() -> None:
    store = SurrealKnowledgeStore(
        SurrealDbReadSettings(endpoint="http://127.0.0.1:9", timeout_seconds=0.1),
        version_prober=_down_version,
    )
    assert isinstance(store, KnowledgeStore)
    assert_read_only_store(store)


def test_health_and_query_are_unavailable_when_endpoint_down() -> None:
    store = SurrealKnowledgeStore(
        SurrealDbReadSettings(endpoint="http://127.0.0.1:9", timeout_seconds=0.2),
        version_prober=_down_version,
    )

    async def _run() -> None:
        health = await store.health()
        assert health.availability is StoreAvailability.UNAVAILABLE
        result = await store.query(
            KnowledgeQuery(
                schema_version=KNOWLEDGE_QUERY_SCHEMA,
                query_id="q-offline",
                text_query="anything",
            )
        )
        assert result.availability is StoreAvailability.UNAVAILABLE
        assert result.hits == ()
        snap = await store.get_snapshot("snap-1")
        assert snap.status is LookupStatus.UNAVAILABLE

    asyncio.run(_run())


def test_version_prefix_mismatch_is_unavailable() -> None:
    def _old_version(_: str, *, timeout_seconds: float) -> SurrealHttpProbeResult:
        del timeout_seconds
        return SurrealHttpProbeResult(ok=True, status_code=200, body_text="surrealdb-2.6.0")

    store = SurrealKnowledgeStore(
        SurrealDbReadSettings(expected_server_version_prefix="surrealdb-3.0"),
        version_prober=_old_version,
    )

    async def _run() -> None:
        health = await store.health()
        assert health.availability is StoreAvailability.UNAVAILABLE
        assert health.detail and "version mismatch" in health.detail

    asyncio.run(_run())


def test_absent_namespace_is_unavailable_not_empty() -> None:
    def _catalog(**_kwargs: object) -> CatalogProbe:
        return CatalogProbe(
            reachable=True,
            namespaces=frozenset({"main", "governance"}),
            namespace_present=False,
            database_present=False,
            detail="configured namespace 'agent_brain' absent",
        )

    store = SurrealKnowledgeStore(
        version_prober=_ok_version,
        catalog_prober=_catalog,
    )

    async def _run() -> None:
        result = await store.query(
            KnowledgeQuery(
                schema_version=KNOWLEDGE_QUERY_SCHEMA,
                query_id="q-ns",
                text_query="alpha",
            )
        )
        assert result.availability is StoreAvailability.UNAVAILABLE
        assert result.hits == ()
        assert result.detail and "agent_brain" in result.detail
        snap = await store.get_snapshot("snap-1")
        assert snap.status is LookupStatus.UNAVAILABLE

    asyncio.run(_run())


def test_present_catalog_returns_available_hits() -> None:
    def _catalog(**_kwargs: object) -> CatalogProbe:
        return CatalogProbe(
            reachable=True,
            namespaces=frozenset({"agent_brain"}),
            namespace_present=True,
            database_present=True,
        )

    def _sql(
        _endpoint: str,
        sql: str,
        *,
        namespace: str,
        database: str,
        timeout_seconds: float,
        authorization: str | None = None,
    ) -> SurrealHttpProbeResult:
        del namespace, database, timeout_seconds, authorization
        assert sql.upper().startswith("SELECT")
        body = (
            '[{"status":"OK","result":[{"id":"repo_artifact:1",'
            '"content_ref":"src/a.py","file_type":"repo_artifact","score":0.8}]}]'
        )
        return SurrealHttpProbeResult(ok=True, status_code=200, body_text=body)

    store = SurrealKnowledgeStore(
        version_prober=_ok_version,
        catalog_prober=_catalog,
        sql_executor=_sql,
        knowledge_tables=("repo_artifact",),
    )

    async def _run() -> None:
        result = await store.query(
            KnowledgeQuery(
                schema_version=KNOWLEDGE_QUERY_SCHEMA,
                query_id="q-hit",
                text_query="a.py",
            )
        )
        assert result.availability is StoreAvailability.AVAILABLE
        assert len(result.hits) == 1
        assert result.hits[0].record_id == "repo_artifact:1"
        snap = await store.get_snapshot("missing")
        assert snap.status is LookupStatus.ABSENT

    asyncio.run(_run())
