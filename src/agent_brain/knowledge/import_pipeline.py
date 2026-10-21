"""Idempotent knowledge import pipeline (Slice 6, T5).

The pipeline reconciles a received knowledge snapshot against the
persisted import state:

- fresh stores are marked ``imported``,
- stores whose persisted state already matches the snapshot are marked
  ``skipped`` without mutation,
- any change replaces the persisted state via reconciliation and is
  marked ``imported`` or ``updated``.

Record identity is ``(source_ref, source_hash)``; metadata-only changes
do not trigger an update. Tombstones mark source refs that disappeared
from the snapshot and are dropped again when the ref reappears.
"""

from __future__ import annotations

from collections.abc import Mapping

from agent_brain.core.time import Clock, utcnow
from agent_brain.knowledge.import_store import (
    IMPORT_RESULT_STATUS_IMPORTED,
    IMPORT_RESULT_STATUS_REJECTED,
    ImportedRecord,
    KnowledgeImportResult,
    KnowledgeImportStore,
    Tombstone,
    validate_snapshot_input,
)
from agent_brain.knowledge.snapshot import KnowledgeSnapshot

IMPORT_PIPELINE_STATUS_UPDATED = "updated"
IMPORT_PIPELINE_STATUS_SKIPPED = "skipped"

RECORD_REMOVED_FROM_SNAPSHOT = "record_removed_from_snapshot"


def import_knowledge_snapshot(
    store: KnowledgeImportStore,
    snapshot_or_payload: KnowledgeSnapshot | str | Mapping[str, object],
    *,
    clock: Clock | None = None,
) -> KnowledgeImportResult:
    """Import one snapshot into the store, idempotently.

    Rejected inputs never mutate the store. Unchanged state is skipped
    without touching stored timestamps. Changed state is reconciled:
    kept records preserve ``imported_at`` and metadata, new records get
    the current import time, and removed source refs gain tombstones.
    """
    report, snapshot = validate_snapshot_input(snapshot_or_payload)
    if report.status != "ok" or snapshot is None:
        return KnowledgeImportResult(
            status=IMPORT_RESULT_STATUS_REJECTED,
            record_count=0,
            tombstone_count=0,
            findings=report.findings,
        )

    now = utcnow(clock).isoformat()
    existing_records = list(store.iter_records())
    existing_tombstones = list(store.current_tombstones())
    fresh_pre_apply = not existing_records and not existing_tombstones
    desired_refs = {manifest.source_ref for manifest in snapshot.manifests}

    existing_by_key = {
        (record.source_ref, record.source_hash): record
        for record in existing_records
    }
    new_records: list[ImportedRecord] = []
    record_count = 0
    for manifest in snapshot.manifests:
        existing = existing_by_key.get((manifest.source_ref, manifest.source_hash))
        if existing is not None:
            new_records.append(existing)
            continue
        new_records.append(
            ImportedRecord(
                source_ref=manifest.source_ref,
                source_hash=manifest.source_hash,
                schema_version=snapshot.metadata.schema_version,
                built_at=snapshot.metadata.built_at,
                tool_version=snapshot.metadata.tool_version,
                imported_at=now,
            )
        )
        record_count += 1

    tombstone_refs = {tombstone.source_ref for tombstone in existing_tombstones}
    new_tombstones: list[Tombstone] = []
    tombstone_count = 0
    for tombstone in existing_tombstones:
        if tombstone.source_ref not in desired_refs:
            new_tombstones.append(tombstone)
    for record in existing_records:
        if record.source_ref in desired_refs:
            continue
        if record.source_ref in tombstone_refs:
            continue
        new_tombstones.append(
            Tombstone(
                source_ref=record.source_ref,
                removed_at=now,
                reason=RECORD_REMOVED_FROM_SNAPSHOT,
            )
        )
        tombstone_count += 1

    state_changed = (new_records != existing_records) or (
        new_tombstones != existing_tombstones
    )
    if not state_changed:
        return KnowledgeImportResult(
            status=IMPORT_PIPELINE_STATUS_SKIPPED,
            record_count=0,
            tombstone_count=0,
            findings=(),
        )

    store.commit_reconciliation(new_records, new_tombstones)
    status = (
        IMPORT_RESULT_STATUS_IMPORTED
        if fresh_pre_apply
        else IMPORT_PIPELINE_STATUS_UPDATED
    )
    return KnowledgeImportResult(
        status=status,
        record_count=record_count,
        tombstone_count=tombstone_count,
        findings=(),
    )
