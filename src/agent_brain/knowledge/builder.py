"""Build deterministic knowledge snapshots from portable ingestion outputs.

Slice 6 contracts:
- The builder consumes a ``RepositoryIngestionResult`` (``repository-ingestion/v1``)
  and produces a ``KnowledgeSnapshot`` (``knowledge-snapshot/v1``).
- Determinism: the snapshot is derived only from portable ingestion outputs.
  Callers inject the clock; without injection a system clock is used so the
  build remains explicit about time.
- Fail-closed provenance: the builder recomputes the ingestion fingerprint and
  rejects a snapshot build when the fingerprint does not match. Every manifest
  entry requires a resolved ``source_hash``.
"""

from __future__ import annotations

from agent_brain.connectors.ingestion import (
    ArtifactRef,
    RepositoryIngestionResult,
    build_ingestion_fingerprint,
)
from agent_brain.core.time import Clock, SystemClock
from agent_brain.knowledge.snapshot import BuildMetadata, KnowledgeManifest, KnowledgeSnapshot

# Keep in sync with pyproject.toml / package SemVer (#17 version source of truth).
DEFAULT_TOOL_VERSION = "agent-brain/0.2.1"


def _require_ingestion_result(
    ingestion_result: RepositoryIngestionResult,
) -> None:
    """Validate the caller input fail-closed before any snapshot is built."""
    if not isinstance(ingestion_result, RepositoryIngestionResult):
        raise TypeError("ingestion_result must be a RepositoryIngestionResult")


def _build_manifest(artifact: ArtifactRef) -> KnowledgeManifest:
    """Validate one artifact provenance pair and return its manifest entry."""
    source_ref = artifact.source_path
    source_hash = artifact.source_hash
    text_fields = {"source_ref": source_ref, "source_hash": source_hash}
    for field_name, value in text_fields.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"{field_name} must be a resolved non-blank string"
            )
    return KnowledgeManifest(source_ref=source_ref, source_hash=source_hash)


def _build_manifests(
    ingestion_result: RepositoryIngestionResult,
) -> tuple[KnowledgeManifest, ...]:
    """Build provenance manifests in deterministic artifact order."""
    manifests: list[KnowledgeManifest] = []
    for artifact in sorted(
        ingestion_result.artifacts, key=lambda item: item.artifact_id
    ):
        manifests.append(_build_manifest(artifact))
    return tuple(manifests)


def build_knowledge_snapshot(
    ingestion_result: RepositoryIngestionResult,
    *,
    clock: Clock | None = None,
    tool_version: str = DEFAULT_TOOL_VERSION,
) -> KnowledgeSnapshot:
    """Build a deterministic knowledge snapshot from an ingestion result."""
    _require_ingestion_result(ingestion_result)
    used_clock = clock or SystemClock()

    expected_fingerprint = build_ingestion_fingerprint(
        source=ingestion_result.source,
        profile_id=ingestion_result.profile_id,
        artifacts=ingestion_result.artifacts,
        records=ingestion_result.records,
        edges=ingestion_result.edges,
        findings=ingestion_result.findings,
    )
    if ingestion_result.fingerprint != expected_fingerprint:
        raise ValueError(
            "ingestion fingerprint mismatch: snapshot build refused because "
            "the declared fingerprint does not match the portable outputs"
        )

    manifests = _build_manifests(ingestion_result)
    metadata = BuildMetadata(
        built_at=used_clock.now().isoformat(), tool_version=tool_version
    )
    return KnowledgeSnapshot(
        schema_version="knowledge-snapshot/v1",
        manifests=manifests,
        metadata=metadata,
    )
