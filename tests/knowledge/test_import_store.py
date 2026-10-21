"""Knowledge import store tests (Slice 6, T4)."""

from __future__ import annotations

from datetime import datetime

import pytest

from agent_brain.connectors.ingestion import (
    INGESTION_RESULT_SCHEMA,
    RepositoryIngestionResult,
    build_ingestion_fingerprint,
)
from agent_brain.contracts import ArtifactRef, IndexRecord, RepositorySource
from agent_brain.core.time import FixedClock
from agent_brain.knowledge.builder import build_knowledge_snapshot
from agent_brain.knowledge.import_store import KnowledgeImportStore

FIXED_TIME = datetime(2026, 1, 1, 12, 0, 0)


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


def _result(
    artifacts: tuple[ArtifactRef, ...], fingerprint: str | None = None
) -> RepositoryIngestionResult:
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
    resolved_fingerprint = fingerprint or build_ingestion_fingerprint(
        source=source,
        profile_id="profile-widgets",
        artifacts=artifacts,
        records=records,
        edges=(),
        findings=(),
    )
    return RepositoryIngestionResult(
        schema_version=INGESTION_RESULT_SCHEMA,
        source=source,
        profile_id="profile-widgets",
        artifacts=artifacts,
        records=records,
        edges=(),
        findings=(),
        fingerprint=resolved_fingerprint,
    )


def _snapshot():
    result = _result(
        (
            _artifact("artifact-widget", "src/widget.py", "a" * 64),
            _artifact("artifact-alpha", "src/alpha.py", "c" * 64),
        )
    )
    return build_knowledge_snapshot(result, clock=FixedClock(FIXED_TIME))


def test_apply_import_stores_records_with_fixed_clock() -> None:
    snapshot = _snapshot()
    clock = FixedClock(FIXED_TIME)
    store = KnowledgeImportStore()

    result = store.apply_import(snapshot, clock=clock)
    records = list(store.iter_records())

    assert result.status == "imported"
    assert result.findings == ()
    assert len(records) == len(snapshot.manifests)
    assert [(record.source_ref, record.source_hash) for record in records] == [
        (manifest.source_ref, manifest.source_hash)
        for manifest in snapshot.manifests
    ]
    assert all(record.imported_at == FIXED_TIME.isoformat() for record in records)
    assert all(
        record.tool_version == snapshot.metadata.tool_version
        and record.schema_version == snapshot.metadata.schema_version
        and record.built_at == snapshot.metadata.built_at
        for record in records
    )


def test_reference_only_is_default_mode() -> None:
    store = KnowledgeImportStore()

    assert store.mode == "reference_only"

    with pytest.raises(ValueError, match="mode"):
        KnowledgeImportStore(mode="productive")


def test_validation_first_rejects_invalid_payload_without_mutation() -> None:
    snapshot = _snapshot()
    clock = FixedClock(FIXED_TIME)
    store = KnowledgeImportStore()

    first = store.apply_import(snapshot, clock=clock)
    assert first.status == "imported"
    records_before = list(store.iter_records())

    second = store.apply_import("{not valid", clock=clock)

    assert second.status == "rejected"
    assert second.record_count == 0
    assert second.findings != ()
    assert list(store.iter_records()) == records_before


def test_initial_state_is_empty() -> None:
    store = KnowledgeImportStore()

    assert list(store.iter_records()) == []
    assert list(store.current_tombstones()) == []
