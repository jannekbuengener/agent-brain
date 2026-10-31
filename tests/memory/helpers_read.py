"""Shared helpers for Memory Read (#11) tests."""

from __future__ import annotations

from datetime import datetime

from agent_brain.contracts.provenance import PROVENANCE_SCHEMA, Provenance
from agent_brain.contracts.resolution import RESOLUTION_META_SCHEMA, ResolutionMeta
from agent_brain.contracts.temporal import TEMPORAL_ENVELOPE_SCHEMA, TemporalEnvelope
from agent_brain.memory.read.models import (
    LIVE_CLAIM_SCHEMA,
    MEMORY_ENTRY_SCHEMA,
    LiveStateClaim,
    MemoryEntry,
)
from agent_brain.memory.scope import MEMORY_SCOPE_SCHEMA, MemoryScope, MemoryScopeKind
from agent_brain.memory.types import MEMORY_RECORD_SCHEMA, MemoryRecord

AS_OF = datetime(2026, 10, 31, 12, 0, 0)
KNOWN_AT = datetime(2026, 10, 31, 11, 0, 0)


def tenant_scope(tenant_id: str = "tenant-a") -> MemoryScope:
    return MemoryScope(
        schema_version=MEMORY_SCOPE_SCHEMA,
        kind=MemoryScopeKind.TENANT,
        tenant_id=tenant_id,
    )


def session_scope(
    *,
    tenant_id: str = "tenant-a",
    agent_id: str = "agent-1",
    session_id: str = "session-1",
) -> MemoryScope:
    return MemoryScope(
        schema_version=MEMORY_SCOPE_SCHEMA,
        kind=MemoryScopeKind.SESSION,
        tenant_id=tenant_id,
        agent_id=agent_id,
        session_id=session_id,
    )


def make_record(
    *,
    record_id: str = "mem-1",
    scope: MemoryScope | None = None,
    subject_ref: str = "subject-1",
    known_at: datetime = KNOWN_AT,
    evidence_refs: tuple[str, ...] = ("ev-1",),
    summary: str | None = "memory summary",
) -> MemoryRecord:
    return MemoryRecord(
        schema_version=MEMORY_RECORD_SCHEMA,
        record_id=record_id,
        subject_ref=subject_ref,
        scope=scope or tenant_scope(),
        content_ref=f"content:{record_id}",
        known_at=known_at,
        summary=summary,
        evidence_refs=evidence_refs,
    )


def make_entry(
    *,
    record: MemoryRecord | None = None,
    known_at: datetime = KNOWN_AT,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    ttl_seconds: int | None = None,
    superseded_by_ref: str | None = None,
    confidence: float | None = 0.8,
    source_trust: float | None = 0.7,
    evidence_refs: tuple[str, ...] | None = None,
    source_kind: str = "repo_doc",
    source_ref: str = "docs/START_HIER.md",
    live_claim: LiveStateClaim | None = None,
    session_id: str | None = "sess-write-1",
    record_id: str = "mem-1",
    scope: MemoryScope | None = None,
) -> MemoryEntry:
    scope = scope or tenant_scope()
    if record is None:
        record = make_record(
            record_id=record_id,
            scope=scope,
            known_at=known_at,
            evidence_refs=("ev-1",) if evidence_refs is None else evidence_refs,
        )
    elif evidence_refs is not None:
        record = MemoryRecord(
            schema_version=record.schema_version,
            record_id=record.record_id,
            subject_ref=record.subject_ref,
            scope=record.scope,
            content_ref=record.content_ref,
            known_at=record.known_at,
            summary=record.summary,
            evidence_refs=evidence_refs,
        )
    return MemoryEntry(
        schema_version=MEMORY_ENTRY_SCHEMA,
        record=record,
        temporal=TemporalEnvelope(
            schema_version=TEMPORAL_ENVELOPE_SCHEMA,
            known_at=record.known_at,
            valid_from=valid_from,
            valid_until=valid_until,
        ),
        provenance=Provenance(
            schema_version=PROVENANCE_SCHEMA,
            source_kind=source_kind,
            source_ref=source_ref,
        ),
        resolution_meta=ResolutionMeta(
            schema_version=RESOLUTION_META_SCHEMA,
            superseded_by_ref=superseded_by_ref,
            confidence=confidence,
            source_trust=source_trust,
        ),
        ttl_seconds=ttl_seconds,
        live_claim=live_claim,
        session_id=session_id,
    )


def issue_open_claim() -> LiveStateClaim:
    return LiveStateClaim(
        schema_version=LIVE_CLAIM_SCHEMA,
        claim_key="issue:11:state",
        asserted_value="open",
        requires_revalidation=True,
    )
