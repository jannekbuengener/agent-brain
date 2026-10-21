"""Contract tests for the knowledge snapshot module (T1)."""

from __future__ import annotations

import pytest

from agent_brain.knowledge.snapshot import (
    KNOWLEDGE_MANIFEST_SCHEMA,
    KNOWLEDGE_SNAPSHOT_SCHEMA,
    BuildMetadata,
    KnowledgeManifest,
    KnowledgeSnapshot,
)


def _build_metadata() -> BuildMetadata:
    return BuildMetadata(
        built_at="2026-10-21T12:00:00Z",
        tool_version="0.0.0",
    )


def _manifest() -> KnowledgeManifest:
    return KnowledgeManifest(
        source_ref="fixtures/connectors/repo",
        source_hash="abc123",
    )


def _snapshot() -> KnowledgeSnapshot:
    return KnowledgeSnapshot(
        metadata=_build_metadata(),
        manifests=(_manifest(),),
    )


class TestSchemaVersionFailClosed:
    """Schema versions are validated against the knowledge-snapshot family."""

    def test_metadata_exposes_canonical_snapshot_schema(self) -> None:
        metadata = BuildMetadata(
            built_at="2026-10-21T12:00:00Z",
            tool_version="0.0.0",
            schema_version=KNOWLEDGE_SNAPSHOT_SCHEMA,
        )
        assert metadata.schema_version == "knowledge-snapshot/v1"
        assert KNOWLEDGE_SNAPSHOT_SCHEMA == "knowledge-snapshot/v1"
        assert KNOWLEDGE_MANIFEST_SCHEMA == "knowledge-manifest/v1"

    def test_snapshot_rejects_wrong_major_version(self) -> None:
        with pytest.raises(ValueError, match="contract major mismatch"):
            KnowledgeSnapshot(
                schema_version="knowledge-snapshot/v2",
                metadata=_build_metadata(),
                manifests=(_manifest(),),
            )

    def test_snapshot_rejects_foreign_family(self) -> None:
        with pytest.raises(ValueError, match="contract family mismatch"):
            KnowledgeSnapshot(
                schema_version="repository-ingestion/v1",
                metadata=_build_metadata(),
                manifests=(_manifest(),),
            )

    def test_metadata_rejects_wrong_major_version(self) -> None:
        with pytest.raises(ValueError, match="contract major mismatch"):
            BuildMetadata(
                built_at="2026-10-21T12:00:00Z",
                tool_version="0.0.0",
                schema_version="knowledge-snapshot/v2",
            )

    def test_metadata_rejects_foreign_family(self) -> None:
        with pytest.raises(ValueError, match="contract family mismatch"):
            BuildMetadata(
                built_at="2026-10-21T12:00:00Z",
                tool_version="0.0.0",
                schema_version="knowledge-manifest/v1",
            )


class TestProvenanceDuty:
    """Knowledge manifests carry mandatory non-blank provenance fields."""

    def test_manifest_requires_non_blank_source_ref(self) -> None:
        with pytest.raises(ValueError, match="source_ref must not be blank"):
            KnowledgeManifest(source_ref="   ", source_hash="abc123")

    def test_manifest_requires_non_blank_source_hash(self) -> None:
        with pytest.raises(ValueError, match="source_hash must not be blank"):
            KnowledgeManifest(source_ref="fixtures/connectors/repo", source_hash="")

    def test_manifest_requires_string_source_ref(self) -> None:
        with pytest.raises(TypeError, match="source_ref must be a string"):
            KnowledgeManifest(source_ref=123, source_hash="abc123")  # type: ignore[arg-type]

    def test_manifest_requires_string_source_hash(self) -> None:
        with pytest.raises(TypeError, match="source_hash must be a string"):
            KnowledgeManifest(source_ref="fixtures/connectors/repo", source_hash=123)  # type: ignore[arg-type]


class TestFrozenImmutability:
    """Knowledge snapshot records are frozen value objects."""

    def test_metadata_is_frozen(self) -> None:
        metadata = _build_metadata()
        with pytest.raises(AttributeError):
            metadata.built_at = "2026-10-22T00:00:00Z"  # type: ignore[misc]

    def test_manifest_is_frozen(self) -> None:
        manifest = _manifest()
        with pytest.raises(AttributeError):
            manifest.source_ref = "other"  # type: ignore[misc]

    def test_snapshot_is_frozen(self) -> None:
        snapshot = _snapshot()
        with pytest.raises(AttributeError):
            snapshot.manifests = ()  # type: ignore[misc]
