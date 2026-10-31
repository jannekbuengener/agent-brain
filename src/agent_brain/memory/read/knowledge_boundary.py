"""Knowledge-Build vs Memory artifact distinction (#11).

KnowledgeStore / KnowledgeSnapshot paths remain separate from MemoryRead.
This module only classifies surfaces — it never promotes Memory into
Knowledge-Build or performs Knowledge writes.
"""

from __future__ import annotations

from agent_brain.memory.read.models import ArtifactKind, MemoryReadResult
from agent_brain.memory.types import KnowledgeResult, KnowledgeSnapshotLookup


def classify_memory_read_result(result: MemoryReadResult) -> ArtifactKind:
    if not isinstance(result, MemoryReadResult):
        raise TypeError("result must be a MemoryReadResult")
    return ArtifactKind.MEMORY


def classify_knowledge_result(
    result: KnowledgeResult | KnowledgeSnapshotLookup,
) -> ArtifactKind:
    if not isinstance(result, (KnowledgeResult, KnowledgeSnapshotLookup)):
        raise TypeError("result must be a KnowledgeResult or KnowledgeSnapshotLookup")
    return ArtifactKind.KNOWLEDGE_BUILD


def assert_not_mixed(
    *,
    memory: MemoryReadResult | None = None,
    knowledge: KnowledgeResult | KnowledgeSnapshotLookup | None = None,
) -> None:
    """Ensure callers do not silently treat Memory and Knowledge as one store."""
    if memory is not None and classify_memory_read_result(memory) is not ArtifactKind.MEMORY:
        raise TypeError("memory result must remain ArtifactKind.MEMORY")
    if knowledge is not None and classify_knowledge_result(knowledge) is not (
        ArtifactKind.KNOWLEDGE_BUILD
    ):
        raise TypeError("knowledge result must remain ArtifactKind.KNOWLEDGE_BUILD")


__all__ = [
    "assert_not_mixed",
    "classify_knowledge_result",
    "classify_memory_read_result",
]
