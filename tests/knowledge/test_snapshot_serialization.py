"""Snapshot serialization tests (Slice 6, T3)."""

from __future__ import annotations

import json
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
from agent_brain.knowledge.serialization import (
    parse_knowledge_snapshot,
    serialize_knowledge_snapshot,
)

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


def test_serialize_then_parse_roundtrip_is_identity() -> None:
    snapshot = _snapshot()

    payload = serialize_knowledge_snapshot(snapshot)
    restored = parse_knowledge_snapshot(payload)

    assert restored == snapshot


def test_serialization_is_deterministic() -> None:
    snapshot = _snapshot()

    first = serialize_knowledge_snapshot(snapshot)
    second = serialize_knowledge_snapshot(snapshot)

    assert first == second
    assert json.loads(first) == json.loads(second)


def test_payload_shape() -> None:
    snapshot = _snapshot()

    payload = json.loads(serialize_knowledge_snapshot(snapshot))

    assert payload["schema_version"] == snapshot.schema_version
    assert payload["metadata"] == {
        "built_at": FIXED_TIME.isoformat(),
        "tool_version": "agent-brain/0.3.4",
        "schema_version": snapshot.metadata.schema_version,
    }
    assert payload["manifests"] == [
        {"source_ref": "src/alpha.py", "source_hash": "c" * 64},
        {"source_ref": "src/widget.py", "source_hash": "a" * 64},
    ]


def test_parse_accepts_mapping_payload() -> None:
    snapshot = _snapshot()

    payload = json.loads(serialize_knowledge_snapshot(snapshot))
    restored = parse_knowledge_snapshot(payload)

    assert restored == snapshot


def test_parse_rejects_foreign_schema_version() -> None:
    snapshot = _snapshot()

    payload = json.loads(serialize_knowledge_snapshot(snapshot))
    payload["schema_version"] = "knowledge-snapshot/v2"

    with pytest.raises(ValueError, match="major mismatch"):
        parse_knowledge_snapshot(payload)


def test_parse_rejects_invalid_json() -> None:
    with pytest.raises(ValueError, match="payload"):
        parse_knowledge_snapshot("{not-json")


def test_parse_rejects_missing_field() -> None:
    snapshot = _snapshot()

    payload = json.loads(serialize_knowledge_snapshot(snapshot))
    del payload["metadata"]

    with pytest.raises(ValueError, match="metadata"):
        parse_knowledge_snapshot(payload)


def test_parse_rejects_bad_manifest_entries() -> None:
    snapshot = _snapshot()

    payload = json.loads(serialize_knowledge_snapshot(snapshot))
    payload["manifests"] = [{"source_ref": "src/widget.py"}]

    with pytest.raises(ValueError, match="source_ref"):
        parse_knowledge_snapshot(payload)
