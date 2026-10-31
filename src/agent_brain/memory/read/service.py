"""Memory Read / Recall service (#11).

Orchestrates: MemoryStore recall → catalog enrichment → provenance gate →
freshness/TTL/supersession derivation → live-state revalidation → consumer
result. Fail-closed throughout. No write / remember / consolidate surface.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from agent_brain.contracts.resolution import ResolutionState
from agent_brain.core.source_priority import SourcePriority
from agent_brain.memory.errors import InvalidMemoryScope, MemoryBoundaryError
from agent_brain.memory.ports import MemoryStore, assert_read_only_store
from agent_brain.memory.read.catalog import MemoryEntryCatalog
from agent_brain.memory.read.freshness import derive_memory_resolution_state
from agent_brain.memory.read.live_state import (
    LiveStateChecker,
    revalidate_against_live_state,
)
from agent_brain.memory.read.models import (
    MEMORY_READ_ITEM_SCHEMA,
    MEMORY_READ_RESULT_SCHEMA,
    ArtifactKind,
    LiveRevalidationStatus,
    MemoryEntry,
    MemoryReadItem,
    MemoryReadResult,
)
from agent_brain.memory.read.provenance_gate import evaluate_provenance_gate
from agent_brain.memory.scope import MemoryScope
from agent_brain.memory.types import (
    MEMORY_RECALL_QUERY_SCHEMA,
    MemoryRecallQuery,
    MemoryRecord,
    StoreAvailability,
    require_memory_scope,
)

_STATE_PRECEDENCE = {
    ResolutionState.UNKNOWN: 3,
    ResolutionState.SUPERSEDED: 2,
    ResolutionState.STALE: 1,
    ResolutionState.CURRENT: 0,
}


def _normalize_as_of(as_of: datetime | None) -> datetime:
    if as_of is None:
        # Explicit as_of is preferred; when omitted use a stable sentinel only
        # for non-temporal fixture paths — callers should pass as_of in tests
        # and production. We still require a datetime object.
        raise ValueError("as_of is required for reproducible memory read evaluation")
    if as_of.tzinfo is None:
        return as_of
    from datetime import UTC

    return as_of.astimezone(UTC).replace(tzinfo=None)


def _merge_state(
    base: ResolutionState,
    forced: ResolutionState | None,
) -> ResolutionState:
    if forced is None:
        return base
    if _STATE_PRECEDENCE[forced] >= _STATE_PRECEDENCE[base]:
        return forced
    return base


def _admissible(
    state: ResolutionState,
    *,
    provenance_passed: bool,
    live_status: LiveRevalidationStatus,
    live_required: bool,
) -> bool:
    if not provenance_passed:
        return False
    if state is not ResolutionState.CURRENT:
        return False
    if live_required and live_status is LiveRevalidationStatus.UNAVAILABLE:
        return False
    return live_status is not LiveRevalidationStatus.CONTRADICTED


@dataclass(frozen=True, slots=True)
class MemoryReadService:
    """Scoped Memory recall evaluator behind existing #39 / #37 contracts."""

    store: MemoryStore
    catalog: MemoryEntryCatalog
    live_checker: LiveStateChecker | None = None
    source_priority: SourcePriority | None = None

    def __post_init__(self) -> None:
        assert_read_only_store(self.store)
        if not isinstance(self.catalog, MemoryEntryCatalog):
            raise TypeError("catalog must be a MemoryEntryCatalog")

    async def recall(
        self,
        query: MemoryRecallQuery,
        *,
        as_of: datetime,
    ) -> MemoryReadResult:
        if not isinstance(query, MemoryRecallQuery):
            raise TypeError("query must be a MemoryRecallQuery")
        require_memory_scope(query.scope)
        evaluated_at = _normalize_as_of(as_of)

        raw = await self.store.recall(query)
        if raw.availability is StoreAvailability.UNAVAILABLE:
            return MemoryReadResult(
                schema_version=MEMORY_READ_RESULT_SCHEMA,
                availability=StoreAvailability.UNAVAILABLE,
                items=(),
                detail=raw.detail or "memory store unavailable",
                limitations=("backend_unavailable",),
                as_of=evaluated_at,
                artifact_kind=ArtifactKind.MEMORY,
            )

        known_ids = {record.record_id for record in raw.records}
        # Also include supersession targets registered in the catalog so chains
        # that point at catalog-only ids can resolve.
        known_ids.update(self.catalog.as_mapping().keys())

        items: list[MemoryReadItem] = []
        limitations: list[str] = []
        for record in raw.records:
            items.append(
                self._evaluate_record(
                    record,
                    as_of=evaluated_at,
                    known_ids=known_ids,
                    limitations=limitations,
                )
            )

        return MemoryReadResult(
            schema_version=MEMORY_READ_RESULT_SCHEMA,
            availability=StoreAvailability.AVAILABLE,
            items=tuple(items),
            detail=None,
            limitations=tuple(sorted(set(limitations))),
            as_of=evaluated_at,
            artifact_kind=ArtifactKind.MEMORY,
        )

    async def recall_for_scope(
        self,
        scope: MemoryScope,
        *,
        as_of: datetime,
        subject_ref: str | None = None,
        limit: int = 20,
        query_id: str = "memory-read",
        text_query: str | None = None,
        known_as_of: datetime | None = None,
    ) -> MemoryReadResult:
        require_memory_scope(scope)
        query = MemoryRecallQuery(
            schema_version=MEMORY_RECALL_QUERY_SCHEMA,
            query_id=query_id,
            scope=scope,
            subject_ref=subject_ref,
            limit=limit,
            known_as_of=known_as_of,
            text_query=text_query,
        )
        return await self.recall(query, as_of=as_of)

    def evaluate_entry(
        self,
        entry: MemoryEntry,
        *,
        as_of: datetime,
        known_supersession_targets: frozenset[str] | set[str] | None = None,
    ) -> MemoryReadItem:
        """Evaluate a single enriched entry without hitting the store."""
        return self._evaluate_entry(
            entry,
            as_of=_normalize_as_of(as_of),
            known_ids=set(known_supersession_targets or ()),
            limitations=[],
        )

    def _evaluate_record(
        self,
        record: MemoryRecord,
        *,
        as_of: datetime,
        known_ids: set[str],
        limitations: list[str],
    ) -> MemoryReadItem:
        entry = self.catalog.get(record.record_id)
        if entry is None:
            limitations.append("missing_entry_metadata")
            # Synthesize a minimal fail-closed item without inventing provenance.
            # We cannot construct MemoryEntry without Provenance; return via a
            # dedicated UNKNOWN item path using evaluate of a placeholder is not
            # possible. Instead raise through a synthetic evaluation helper.
            return self._missing_metadata_item(record, as_of=as_of)
        if not entry.record.scope.matches(record.scope):
            raise MemoryBoundaryError(
                "catalog scope isolation violation for "
                f"record_id={record.record_id!r}"
            )
        return self._evaluate_entry(
            entry,
            as_of=as_of,
            known_ids=known_ids,
            limitations=limitations,
        )

    def _missing_metadata_item(
        self,
        record: MemoryRecord,
        *,
        as_of: datetime,
    ) -> MemoryReadItem:
        """Build a non-admissible UNKNOWN item when catalog metadata is absent.

        Uses empty/minimal #37 objects only to satisfy type construction; the
        provenance gate and forced UNKNOWN ensure they are never load-bearing.
        """
        from agent_brain.contracts.provenance import PROVENANCE_SCHEMA, Provenance
        from agent_brain.contracts.resolution import (
            RESOLUTION_META_SCHEMA,
            ResolutionMeta,
        )
        from agent_brain.contracts.temporal import (
            TEMPORAL_ENVELOPE_SCHEMA,
            TemporalEnvelope,
        )
        from agent_brain.memory.read.models import MEMORY_ENTRY_SCHEMA

        placeholder = MemoryEntry(
            schema_version=MEMORY_ENTRY_SCHEMA,
            record=record,
            temporal=TemporalEnvelope(
                schema_version=TEMPORAL_ENVELOPE_SCHEMA,
                known_at=record.known_at,
            ),
            provenance=Provenance(
                schema_version=PROVENANCE_SCHEMA,
                source_kind="missing",
                source_ref="missing",
            ),
            resolution_meta=ResolutionMeta(schema_version=RESOLUTION_META_SCHEMA),
        )
        # Force UNKNOWN regardless of placeholder provenance content.
        return MemoryReadItem(
            schema_version=MEMORY_READ_ITEM_SCHEMA,
            entry=placeholder,
            resolution_state=ResolutionState.UNKNOWN,
            reason_codes=("missing_entry_metadata",),
            admissible_as_context=False,
            artifact_kind=ArtifactKind.MEMORY,
            live_revalidation=None,
            explanation=(
                "No MemoryEntry metadata registered; "
                "MISSING_METADATA != TRUSTED."
            ),
        )

    def _evaluate_entry(
        self,
        entry: MemoryEntry,
        *,
        as_of: datetime,
        known_ids: set[str],
        limitations: list[str],
    ) -> MemoryReadItem:
        gate = evaluate_provenance_gate(entry)
        freshness = derive_memory_resolution_state(
            entry,
            as_of=as_of,
            known_supersession_targets=known_ids,
        )
        live = revalidate_against_live_state(
            entry,
            checker=self.live_checker,
            source_priority=self.source_priority,
        )

        state = freshness.resolution_state
        reasons: list[str] = list(freshness.reason_codes)

        if not gate.passed:
            state = _merge_state(state, gate.forced_state)
            reasons.extend(gate.reason_codes)
            limitations.append("provenance_gate_failed")
        elif gate.reason_codes:
            reasons.extend(gate.reason_codes)
            limitations.extend(gate.reason_codes)

        live_required = bool(
            entry.live_claim is not None and entry.live_claim.requires_revalidation
        )
        if live.status is LiveRevalidationStatus.CONTRADICTED:
            state = _merge_state(state, ResolutionState.STALE)
            reasons.append("live_contradicts_memory")
            limitations.append("live_state_overrides_memory")
        elif live.status is LiveRevalidationStatus.UNAVAILABLE and live_required:
            state = _merge_state(state, ResolutionState.UNKNOWN)
            reasons.append(live.reason_code or "live_check_unavailable")
            limitations.append("live_revalidation_unavailable")
        elif live.status is LiveRevalidationStatus.CONFIRMED:
            reasons.append("live_confirmed")

        # Deduplicate reason codes while preserving order.
        seen: set[str] = set()
        ordered_reasons: list[str] = []
        for code in reasons:
            if code not in seen:
                seen.add(code)
                ordered_reasons.append(code)

        admissible = _admissible(
            state,
            provenance_passed=gate.passed,
            live_status=live.status,
            live_required=live_required,
        )

        explanation_parts = [freshness.explanation]
        if not gate.passed:
            explanation_parts.append(gate.explanation)
        if live.reason_code:
            explanation_parts.append(f"live:{live.reason_code}")

        return MemoryReadItem(
            schema_version=MEMORY_READ_ITEM_SCHEMA,
            entry=entry,
            resolution_state=state,
            reason_codes=tuple(ordered_reasons),
            admissible_as_context=admissible,
            artifact_kind=ArtifactKind.MEMORY,
            live_revalidation=live,
            explanation="; ".join(part for part in explanation_parts if part),
        )


def assert_scopes_isolated(
    items: Sequence[MemoryReadItem],
    expected_scope: MemoryScope,
) -> None:
    """Fail closed if any evaluated item escapes the expected scope."""
    validated = require_memory_scope(expected_scope)
    for item in items:
        if not item.entry.record.scope.matches(validated):
            raise InvalidMemoryScope(
                "scope isolation violation: "
                f"item {item.entry.record.record_id!r} does not match expected scope"
            )


__all__ = [
    "MemoryReadService",
    "assert_scopes_isolated",
]
