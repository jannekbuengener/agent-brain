"""Neutral knowledge import store (Slice 6, T4).

The import store consumes validated knowledge snapshots and derives
imported records from their manifests. It is reference-only by default
and follows a validation-first contract: rejected inputs never mutate
the store.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from agent_brain.core.time import Clock
from agent_brain.knowledge.serialization import parse_knowledge_snapshot
from agent_brain.knowledge.snapshot import KnowledgeSnapshot

ALLOWED_IMPORT_MODES: frozenset[str] = frozenset({"reference_only"})

IMPORT_RESULT_STATUS_IMPORTED = "imported"
IMPORT_RESULT_STATUS_REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class SnapshotValidationReport:
    """Validation-first outcome of inspecting a snapshot input."""

    status: str
    findings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ImportedRecord:
    """One manifest-derived record with import provenance."""

    source_ref: str
    source_hash: str
    schema_version: str
    built_at: str
    tool_version: str
    imported_at: str


@dataclass(frozen=True, slots=True)
class Tombstone:
    """Record of a source that is no longer present in a snapshot."""

    source_ref: str
    removed_at: str
    reason: str


@dataclass(frozen=True, slots=True)
class KnowledgeImportResult:
    """Result of applying one import step against the store."""

    status: str
    record_count: int
    tombstone_count: int
    findings: tuple[str, ...]


class KnowledgeImportStore:
    """Validation-first, reference-only store for imported snapshots."""

    def __init__(self, mode: str = "reference_only") -> None:
        if mode not in ALLOWED_IMPORT_MODES:
            raise ValueError(f"unsupported mode: {mode!r}")
        self.mode = mode
        self._records: list[ImportedRecord] = []
        self._tombstones: list[Tombstone] = []

    def apply_import(
        self,
        snapshot_or_payload: KnowledgeSnapshot | str | Mapping[str, object],
        *,
        clock: Clock,
    ) -> KnowledgeImportResult:
        """Validate first, then derive records from manifest entries.

        Rejected inputs produce a rejected result with findings and
        never mutate the store.
        """
        report, snapshot = self._validate_input(snapshot_or_payload)
        if report.status != "ok" or snapshot is None:
            return KnowledgeImportResult(
                status=IMPORT_RESULT_STATUS_REJECTED,
                record_count=0,
                tombstone_count=0,
                findings=report.findings,
            )

        imported_at = clock.now().isoformat()
        new_records = [
            ImportedRecord(
                source_ref=manifest.source_ref,
                source_hash=manifest.source_hash,
                schema_version=snapshot.metadata.schema_version,
                built_at=snapshot.metadata.built_at,
                tool_version=snapshot.metadata.tool_version,
                imported_at=imported_at,
            )
            for manifest in snapshot.manifests
        ]
        self._records.extend(new_records)
        return KnowledgeImportResult(
            status=IMPORT_RESULT_STATUS_IMPORTED,
            record_count=len(new_records),
            tombstone_count=len(self._tombstones),
            findings=(),
        )

    def iter_records(self) -> tuple[ImportedRecord, ...]:
        """Return a defensive copy of the imported records."""
        return tuple(self._records)

    def current_tombstones(self) -> tuple[Tombstone, ...]:
        """Return a defensive copy of the current tombstones."""
        return tuple(self._tombstones)

    def _validate_input(
        self,
        snapshot_or_payload: KnowledgeSnapshot | str | Mapping[str, object],
    ) -> tuple[SnapshotValidationReport, KnowledgeSnapshot | None]:
        if isinstance(snapshot_or_payload, KnowledgeSnapshot):
            snapshot = snapshot_or_payload
        else:
            try:
                snapshot = parse_knowledge_snapshot(snapshot_or_payload)
            except (TypeError, ValueError) as exc:
                return (
                    SnapshotValidationReport(
                        status="rejected",
                        findings=(f"invalid snapshot payload: {exc}",),
                    ),
                    None,
                )
        if not snapshot.manifests:
            return (
                SnapshotValidationReport(
                    status="rejected",
                    findings=("snapshot contains no manifests",),
                ),
                None,
            )
        return (
            SnapshotValidationReport(status="ok", findings=()),
            snapshot,
        )
