"""SurrealDB-backed MemoryStore adapter (#10) behind #39 ports.

Fail-closed when endpoint/catalog mapping is unusable. Does not invent empty
memory recalls for a missing namespace/database and never exposes write methods.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from datetime import datetime

from agent_brain.memory.ports import assert_read_only_store
from agent_brain.memory.scope import MemoryScope
from agent_brain.memory.types import (
    MEMORY_RECALL_RESULT_SCHEMA,
    STORE_HEALTH_SCHEMA,
    MemoryRecallQuery,
    MemoryRecallResult,
    StoreAvailability,
    StoreHealth,
    require_memory_scope,
)
from agent_brain.surrealdb.catalog import CatalogProbe, probe_configured_catalog
from agent_brain.surrealdb.config import SurrealDbReadSettings
from agent_brain.surrealdb.http import SurrealHttpProbeResult, post_sql, probe_version

VersionProber = Callable[..., SurrealHttpProbeResult]
CatalogProber = Callable[..., CatalogProbe]
SqlExecutor = Callable[..., SurrealHttpProbeResult]


class SurrealMemoryStore:
    """Native Surreal memory read adapter with explicit UNAVAILABLE semantics."""

    def __init__(
        self,
        settings: SurrealDbReadSettings | None = None,
        *,
        version_prober: VersionProber | None = None,
        catalog_prober: CatalogProber | None = None,
        sql_executor: SqlExecutor | None = None,
        memory_tables: Sequence[str] | None = None,
    ) -> None:
        self._settings = settings or SurrealDbReadSettings()
        self._version_prober = version_prober or probe_version
        self._catalog_prober = catalog_prober or probe_configured_catalog
        self._sql_executor = sql_executor or post_sql
        self._memory_tables = tuple(
            memory_tables
            if memory_tables is not None
            else ("agent_memory", "shared_memory")
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
            return StoreHealth(
                schema_version=STORE_HEALTH_SCHEMA,
                availability=StoreAvailability.UNAVAILABLE,
                detail=probe.error or f"surreal version probe failed ({probe.status_code})",
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

    async def _unavailable_detail(self) -> str | None:
        health = await self.health()
        if health.availability is StoreAvailability.UNAVAILABLE:
            return health.detail or "surreal memory store unavailable"
        catalog = await self._catalog()
        if not catalog.reachable:
            return catalog.detail or "surreal catalog unreachable"
        if catalog.namespace_present is not True:
            return catalog.detail or (
                f"configured namespace {self._settings.namespace!r} absent"
            )
        if catalog.database_present is not True:
            return catalog.detail or (
                f"configured database {self._settings.database!r} absent in "
                f"namespace {self._settings.namespace!r}"
            )
        return None

    async def recall(self, query: MemoryRecallQuery) -> MemoryRecallResult:
        if not isinstance(query, MemoryRecallQuery):
            raise TypeError("query must be a MemoryRecallQuery")
        require_memory_scope(query.scope)
        detail = await self._unavailable_detail()
        if detail is not None:
            return MemoryRecallResult(
                schema_version=MEMORY_RECALL_RESULT_SCHEMA,
                availability=StoreAvailability.UNAVAILABLE,
                records=(),
                detail=detail,
            )
        # Mapped NS/DB present, but agent_memory tables are ABSENT on the verified
        # #38 volume. Returning AVAILABLE+empty would claim a successful empty
        # recall; keep UNAVAILABLE until a real table mapping is proven present.
        return MemoryRecallResult(
            schema_version=MEMORY_RECALL_RESULT_SCHEMA,
            availability=StoreAvailability.UNAVAILABLE,
            records=(),
            detail=(
                "surreal memory tables not verified present for "
                f"{self._settings.namespace}/{self._settings.database} "
                f"(expected one of {list(self._memory_tables)})"
            ),
        )

    async def history(
        self,
        subject_ref: str,
        *,
        scope: MemoryScope,
        known_as_of: datetime | None = None,
    ) -> MemoryRecallResult:
        del known_as_of
        if not isinstance(subject_ref, str) or not subject_ref.strip():
            raise ValueError("subject_ref must be a non-blank string")
        require_memory_scope(scope)
        detail = await self._unavailable_detail()
        if detail is not None:
            return MemoryRecallResult(
                schema_version=MEMORY_RECALL_RESULT_SCHEMA,
                availability=StoreAvailability.UNAVAILABLE,
                records=(),
                detail=detail,
            )
        return MemoryRecallResult(
            schema_version=MEMORY_RECALL_RESULT_SCHEMA,
            availability=StoreAvailability.UNAVAILABLE,
            records=(),
            detail=(
                "surreal memory history path not verified present for "
                f"{self._settings.namespace}/{self._settings.database}"
            ),
        )
