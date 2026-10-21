"""Idempotent knowledge import pipeline tests (Slice 6, T5)."""

from __future__ import annotations

from datetime import datetime

from agent_brain.connectors.ingestion import (
    INGESTION_RESULT_SCHEMA,
    RepositoryIngestionResult,
    build_ingestion_fingerprint,
)
from agent_brain.contracts import ArtifactRef, IndexRecord, RepositorySource
from agent_brain.core.time import FixedClock
from agent_brain.knowledge.builder import build_knowledge_snapshot
from agent_brain.knowledge.import_pipeline import import_knowledge_snapshot
from agent_brain.knowledge.import_store import KnowledgeImportStore

FIXED_TIME = datetime(2026, 1, 1, 12, 0, 0)
TIME_2 = datetime(2026, 1, 2, 12, 0, 0)
TIME_3 = datetime(2026, 1, 3, 12, 0, 0)


def _source() -> RepositorySource:
    return RepositorySource(
        schema_version="repository-source/v1",
        source_id="source-widgets",
        repository="example/widgets",
        revision="abc123",
        source_uri="https://example.invalid/widgets.git",
    )


def _artifact(artifact_id: str, source_path: str, source_hash: str) -> ArtifactRef:
    return ArtifactRef(
        schema_version="artifact-ref/v1",
        artifact_id=artifact_id,
        source_id="source-widgets",
        source_path=source_path,
        source_hash=source_hash,
        revision="abc123",
    )


def _result(artifacts: tuple[ArtifactRef, ...]) -> RepositoryIngestionResult:
    source = _source()
    records = tuple(
        IndexRecord(
            schema_version="index-record/v1",
            record_id=f"record-{artifact.artifact_id}",
            record_type="code_symbol",
            source=artifact,
            content_hash="b" * 64,
            attributes={"name": "Widget"},
        )
        for artifact in artifacts
    )
    return RepositoryIngestionResult(
        schema_version=INGESTION_RESULT_SCHEMA,
        source=source,
        profile_id="profile-widgets",
        artifacts=artifacts,
        records=records,
        edges=(),
        findings=(),
        fingerprint=build_ingestion_fingerprint(
            source=source,
            profile_id="profile-widgets",
            artifacts=artifacts,
            records=records,
            edges=(),
            findings=(),
        ),
    )


def _widgets_snapshot():
    result = _result(
        (
            _artifact("artifact-widget", "src/widget.py", "a" * 64),
            _artifact("artifact-alpha", "src/alpha.py", "c" * 64),
        )
    )
    return build_knowledge_snapshot(result, clock=FixedClock(FIXED_TIME))


def _changed_widget_snapshot():
    result = _result(
        (
            _artifact("artifact-widget", "src/widget.py", "d" * 64),
            _artifact("artifact-alpha", "src/alpha.py", "c" * 64),
        )
    )
    return build_knowledge_snapshot(result, clock=FixedClock(TIME_2))


def _alpha_only_snapshot():
    result = _result((_artifact("artifact-alpha", "src/alpha.py", "c" * 64),))
    return build_knowledge_snapshot(result, clock=FixedClock(TIME_2))


def test_import_knowledge_snapshot_imported_on_first_use() -> None:
    snapshot = _widgets_snapshot()
    store = KnowledgeImportStore()

    result = import_knowledge_snapshot(store, snapshot, clock=FixedClock(FIXED_TIME))
    records = list(store.iter_records())

    assert result.status == "imported"
    assert result.record_count == 2
    assert result.tombstone_count == 0
    assert result.findings == ()
    assert sorted(record.source_ref for record in records) == [
        "src/alpha.py",
        "src/widget.py",
    ]
    assert all(record.imported_at == FIXED_TIME.isoformat() for record in records)


def test_identical_replay_is_skipped_without_mutation() -> None:
    snapshot = _widgets_snapshot()
    store = KnowledgeImportStore()
    import_knowledge_snapshot(store, snapshot, clock=FixedClock(FIXED_TIME))

    result = import_knowledge_snapshot(store, snapshot, clock=FixedClock(TIME_2))
    records = list(store.iter_records())

    assert result.status == "skipped"
    assert result.record_count == 0
    assert result.tombstone_count == 0
    assert len(records) == 2
    assert all(record.imported_at == FIXED_TIME.isoformat() for record in records)


def test_changed_source_hash_replaces_record() -> None:
    fresh_snapshot = _widgets_snapshot()
    changed_snapshot = _changed_widget_snapshot()
    store = KnowledgeImportStore()
    import_knowledge_snapshot(store, fresh_snapshot, clock=FixedClock(FIXED_TIME))

    result = import_knowledge_snapshot(
        store, changed_snapshot, clock=FixedClock(TIME_2)
    )
    records = {(record.source_ref, record.source_hash): record for record in store.iter_records()}

    assert result.status == "updated"
    assert result.record_count == 1
    assert result.tombstone_count == 0
    assert records[("src/widget.py", "d" * 64)].imported_at == TIME_2.isoformat()
    assert records[("src/alpha.py", "c" * 64)].imported_at == FIXED_TIME.isoformat()
    assert ("src/widget.py", "a" * 64) not in records


def test_removed_source_creates_tombstone() -> None:
    fresh_snapshot = _widgets_snapshot()
    alpha_snapshot = _alpha_only_snapshot()
    store = KnowledgeImportStore()
    import_knowledge_snapshot(store, fresh_snapshot, clock=FixedClock(FIXED_TIME))

    result = import_knowledge_snapshot(
        store, alpha_snapshot, clock=FixedClock(TIME_2)
    )
    records = list(store.iter_records())
    tombstones = list(store.current_tombstones())

    assert result.status == "updated"
    assert result.record_count == 0
    assert result.tombstone_count == 1
    assert [record.source_ref for record in records] == ["src/alpha.py"]
    assert len(tombstones) == 1
    assert tombstones[0].source_ref == "src/widget.py"
    assert tombstones[0].removed_at == TIME_2.isoformat()
    assert tombstones[0].reason == "record_removed_from_snapshot"


def test_reappearing_source_clears_tombstone() -> None:
    fresh_snapshot = _widgets_snapshot()
    alpha_snapshot = _alpha_only_snapshot()
    store = KnowledgeImportStore()
    import_knowledge_snapshot(store, fresh_snapshot, clock=FixedClock(FIXED_TIME))
    import_knowledge_snapshot(store, alpha_snapshot, clock=FixedClock(TIME_2))

    result = import_knowledge_snapshot(
        store, fresh_snapshot, clock=FixedClock(TIME_3)
    )
    records = {
        record.source_ref: record for record in store.iter_records()
    }
    tombstones = store.current_tombstones()

    assert result.status == "updated"
    assert result.record_count == 1
    assert result.tombstone_count == 0
    assert tombstones == ()
    assert records["src/widget.py"].source_hash == "a" * 64
    assert records["src/widget.py"].imported_at == TIME_3.isoformat()
    assert records["src/alpha.py"].imported_at == FIXED_TIME.isoformat()


def test_repeating_tombstoned_state_is_skipped() -> None:
    fresh_snapshot = _widgets_snapshot()
    alpha_snapshot = _alpha_only_snapshot()
    store = KnowledgeImportStore()
    import_knowledge_snapshot(store, fresh_snapshot, clock=FixedClock(FIXED_TIME))
    import_knowledge_snapshot(store, alpha_snapshot, clock=FixedClock(TIME_2))

    result = import_knowledge_snapshot(
        store, alpha_snapshot, clock=FixedClock(TIME_3)
    )
    tombstones = list(store.current_tombstones())

    assert result.status == "skipped"
    assert result.record_count == 0
    assert result.tombstone_count == 0
    assert len(tombstones) == 1
    assert tombstones[0].removed_at == TIME_2.isoformat()


def test_rejected_payload_does_not_mutate_store() -> None:
    snapshot = _widgets_snapshot()
    store = KnowledgeImportStore()
    import_knowledge_snapshot(store, snapshot, clock=FixedClock(FIXED_TIME))

    result = import_knowledge_snapshot(
        store, "{not valid", clock=FixedClock(TIME_2)
    )
    records = list(store.iter_records())

    assert result.status == "rejected"
    assert result.record_count == 0
    assert result.tombstone_count == 0
    assert result.findings != ()
    assert len(records) == 2
    assert all(record.imported_at == FIXED_TIME.isoformat() for record in records)
