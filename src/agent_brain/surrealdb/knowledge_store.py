"""SurrealDB-backed KnowledgeStore adapter (#10) behind #39 ports.

Fail-closed rules:
- unreachable / version mismatch → UNAVAILABLE
- configured namespace or database absent → UNAVAILABLE (never empty hits)
- write-like statements never leave this adapter
- no Docker/datastore start happens here
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from agent_brain.memory.ports import assert_read_only_store
from agent_brain.memory.types import (
    KNOWLEDGE_RESULT_SCHEMA,
    KNOWLEDGE_SNAPSHOT_LOOKUP_SCHEMA,
    STORE_HEALTH_SCHEMA,
    KnowledgeHit,
    KnowledgeQuery,
    KnowledgeResult,
    KnowledgeSnapshotLookup,
    LookupStatus,
    StoreAvailability,
    StoreHealth,
)
from agent_brain.surrealdb.catalog import CatalogProbe, probe_configured_catalog
from agent_brain.surrealdb.config import SurrealDbReadSettings
from agent_brain.surrealdb.http import (
    SurrealHttpProbeResult,
    parse_json_body,
    post_sql,
    probe_version,
)
from agent_brain.surrealdb.statement_guard import (
    WriteDeniedError,
    classify_readonly_statement,
)

VersionProber = Callable[..., SurrealHttpProbeResult]
CatalogProber = Callable[..., CatalogProbe]
SqlExecutor = Callable[..., SurrealHttpProbeResult]


def _rows_from_sql_payload(payload: Any) -> list[Mapping[str, Any]]:
    if not isinstance(payload, list):
        return []
    rows: list[Mapping[str, Any]] = []
    for entry in payload:
        if not isinstance(entry, Mapping):
            continue
        if entry.get("status") not in (None, "OK"):
            continue
        result = entry.get("result")
        if isinstance(result, list):
            for row in result:
                if isinstance(row, Mapping):
                    rows.append(row)
    return rows


def _hit_from_row(row: Mapping[str, Any], *, fallback_type: str) -> KnowledgeHit | None:
    record_id = row.get("id") or row.get("record_id")
    if record_id is None:
        return None
    content_ref = row.get("content_ref") or row.get("source_path") or str(record_id)
    record_type = row.get("record_type") or row.get("file_type") or fallback_type
    summary = row.get("summary")
    if summary is not None and not isinstance(summary, str):
        summary = str(summary)
    score_raw = row.get("score", 1.0)
    try:
        score = float(score_raw)
    except (TypeError, ValueError):
        score = 1.0
    score = min(1.0, max(0.0, score))
    return KnowledgeHit(
        record_id=str(record_id),
        record_type=str(record_type),
        content_ref=str(content_ref),
        score=score,
        summary=summary,
    )


class SurrealKnowledgeStore:
    """Native Surreal read adapter with explicit UNAVAILABLE semantics."""

    def __init__(
        self,
        settings: SurrealDbReadSettings | None = None,
        *,
        version_prober: VersionProber | None = None,
        catalog_prober: CatalogProber | None = None,
        sql_executor: SqlExecutor | None = None,
        knowledge_tables: Sequence[str] | None = None,
    ) -> None:
        self._settings = settings or SurrealDbReadSettings()
        self._version_prober = version_prober or probe_version
        self._catalog_prober = catalog_prober or probe_configured_catalog
        self._sql_executor = sql_executor or post_sql
        self._knowledge_tables = tuple(
            knowledge_tables
            if knowledge_tables is not None
            else (
                "repo_artifact",
                "doc_page",
                "doc_section",
                "doc_chunk",
                "code_symbol",
            )
        )
        assert_read_only_store(self)

    @property
    def settings(self) -> SurrealDbReadSettings:
        return self._settings

    async def health(self) -> StoreHealth:
        probe = await asyncio.to_thread(
            self._version_prober,
            self._settings.endpoint,
            timeout_seconds=self._settings.timeout_seconds,
        )
        if not probe.ok:
            detail = probe.error or f"surreal version probe failed ({probe.status_code})"
            return StoreHealth(
                schema_version=STORE_HEALTH_SCHEMA,
                availability=StoreAvailability.UNAVAILABLE,
                detail=detail,
            )
        version = probe.version_text or ""
        prefix = self._settings.expected_server_version_prefix
        if prefix and not version.startswith(prefix):
            return StoreHealth(
                schema_version=STORE_HEALTH_SCHEMA,
                availability=StoreAvailability.UNAVAILABLE,
                detail=f"server version mismatch: got {version!r}, expected prefix {prefix!r}",
            )
        return StoreHealth(
            schema_version=STORE_HEALTH_SCHEMA,
            availability=StoreAvailability.AVAILABLE,
            detail=version or None,
        )

    async def _catalog(self) -> CatalogProbe:
        return await asyncio.to_thread(
            self._catalog_prober,
            endpoint=self._settings.endpoint,
            namespace=self._settings.namespace,
            database=self._settings.database,
            timeout_seconds=self._settings.timeout_seconds,
            sql_executor=self._sql_executor,
        )

    async def _ensure_mapped_store(self) -> StoreHealth | KnowledgeResult | None:
        """Return UNAVAILABLE result/health detail object when mapping is unusable.

        Returns None when endpoint is up and configured NS/DB are present.
        """
        health = await self.health()
        if health.availability is StoreAvailability.UNAVAILABLE:
            return health
        catalog = await self._catalog()
        if not catalog.reachable:
            return StoreHealth(
                schema_version=STORE_HEALTH_SCHEMA,
                availability=StoreAvailability.UNAVAILABLE,
                detail=catalog.detail or "surreal catalog unreachable",
            )
        if catalog.namespace_present is not True:
            return StoreHealth(
                schema_version=STORE_HEALTH_SCHEMA,
                availability=StoreAvailability.UNAVAILABLE,
                detail=catalog.detail
                or f"configured namespace {self._settings.namespace!r} absent",
            )
        if catalog.database_present is not True:
            return StoreHealth(
                schema_version=STORE_HEALTH_SCHEMA,
                availability=StoreAvailability.UNAVAILABLE,
                detail=catalog.detail
                or (
                    f"configured database {self._settings.database!r} absent in "
                    f"namespace {self._settings.namespace!r}"
                ),
            )
        return None

    def _unavailable_result(self, detail: str) -> KnowledgeResult:
        return KnowledgeResult(
            schema_version=KNOWLEDGE_RESULT_SCHEMA,
            availability=StoreAvailability.UNAVAILABLE,
            hits=(),
            detail=detail,
        )

    async def query(self, query: KnowledgeQuery) -> KnowledgeResult:
        if not isinstance(query, KnowledgeQuery):
            raise TypeError("query must be a KnowledgeQuery")
        gate = await self._ensure_mapped_store()
        if isinstance(gate, StoreHealth):
            return self._unavailable_result(
                gate.detail or "surreal knowledge store unavailable"
            )

        hits: list[KnowledgeHit] = []
        for table in self._knowledge_tables:
            if query.record_type_filter and table not in query.record_type_filter:
                continue
            # SurrealQL string literal escaping: escape backslash then single quote.
            needle = query.text_query.replace("\\", "\\\\").replace("'", "\\'")
            statement = (
                f"SELECT * FROM {table} "
                f"WHERE string::lowercase(type::string(id)) CONTAINS "
                f"string::lowercase('{needle}') "
                f"OR string::lowercase(type::string(content_ref)) CONTAINS "
                f"string::lowercase('{needle}') "
                f"LIMIT {query.limit}"
            )
            try:
                classify_readonly_statement(statement)
            except WriteDeniedError as exc:
                return self._unavailable_result(f"statement denied: {exc}")

            probe = await asyncio.to_thread(
                self._sql_executor,
                self._settings.endpoint,
                statement,
                namespace=self._settings.namespace,
                database=self._settings.database,
                timeout_seconds=self._settings.timeout_seconds,
            )
            if not probe.ok:
                # Missing table / query errors must not become EMPTY success.
                if probe.status_code == 400 and probe.body_text and "NotFound" in probe.body_text:
                    continue
                return self._unavailable_result(
                    probe.error or f"surreal query failed ({probe.status_code})"
                )
            for row in _rows_from_sql_payload(parse_json_body(probe.body_text)):
                hit = _hit_from_row(row, fallback_type=table)
                if hit is not None:
                    hits.append(hit)
            if len(hits) >= query.limit:
                break

        return KnowledgeResult(
            schema_version=KNOWLEDGE_RESULT_SCHEMA,
            availability=StoreAvailability.AVAILABLE,
            hits=tuple(hits[: query.limit]),
            detail=None,
        )

    async def get_snapshot(self, snapshot_ref: str) -> KnowledgeSnapshotLookup:
        if not isinstance(snapshot_ref, str) or not snapshot_ref.strip():
            raise ValueError("snapshot_ref must be a non-blank string")
        ref = snapshot_ref.strip()
        gate = await self._ensure_mapped_store()
        if isinstance(gate, StoreHealth):
            return KnowledgeSnapshotLookup(
                schema_version=KNOWLEDGE_SNAPSHOT_LOOKUP_SCHEMA,
                status=LookupStatus.UNAVAILABLE,
                snapshot_ref=ref,
                detail=gate.detail or "surreal knowledge store unavailable",
            )
        # Snapshot documents are not yet projected from Surreal tables in this slice.
        return KnowledgeSnapshotLookup(
            schema_version=KNOWLEDGE_SNAPSHOT_LOOKUP_SCHEMA,
            status=LookupStatus.ABSENT,
            snapshot_ref=ref,
            detail="snapshot not found in surreal knowledge mapping",
        )
