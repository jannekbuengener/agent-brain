"""Deterministic knowledge snapshot builder tests (Slice 6, T2)."""

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


def test_two_builds_are_identical_with_fixed_clock() -> None:
    result = _result((_artifact("artifact-widget", "src/widget.py", "a" * 64),))
    clock = FixedClock(FIXED_TIME)

    first = build_knowledge_snapshot(result, clock=clock)
    second = build_knowledge_snapshot(result, clock=clock)

    assert first == second


def test_built_at_and_tool_version_come_from_injection() -> None:
    result = _result((_artifact("artifact-widget", "src/widget.py", "a" * 64),))

    snapshot = build_knowledge_snapshot(result, clock=FixedClock(FIXED_TIME))

    assert snapshot.metadata.built_at == FIXED_TIME.isoformat()
    assert snapshot.metadata.tool_version == "agent-brain/0.3.1"


def test_manifests_map_artifacts_sorted_by_artifact_id() -> None:
    widgets = _artifact("artifact-widget", "src/widget.py", "a" * 64)
    alpha = _artifact("artifact-alpha", "src/alpha.py", "c" * 64)
    result = _result((widgets, alpha))

    snapshot = build_knowledge_snapshot(result, clock=FixedClock(FIXED_TIME))

    assert [manifest.source_ref for manifest in snapshot.manifests] == [
        "src/alpha.py",
        "src/widget.py",
    ]
    assert [manifest.source_hash for manifest in snapshot.manifests] == [
        "c" * 64,
        "a" * 64,
    ]


@pytest.mark.parametrize("bad_hash", ["", "   "])
def test_blank_source_hash_fails_closed(bad_hash: str) -> None:
    artifact = _artifact("artifact-widget", "src/widget.py", "a" * 64)
    object.__setattr__(artifact, "source_hash", bad_hash)
    result = _result((artifact,))

    with pytest.raises(ValueError, match="source_hash"):
        build_knowledge_snapshot(result, clock=FixedClock(FIXED_TIME))


def test_tampered_fingerprint_fails_closed() -> None:
    widgets = _artifact("artifact-widget", "src/widget.py", "a" * 64)
    result = _result((widgets,), fingerprint="0" * 64)

    with pytest.raises(ValueError, match="fingerprint"):
        build_knowledge_snapshot(result, clock=FixedClock(FIXED_TIME))
