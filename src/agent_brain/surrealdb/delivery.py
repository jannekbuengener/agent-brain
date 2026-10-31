"""Coordinated #10+#21 delivery surface for Goal #67.

Builds read stores and the state-handoff decision from the same
``SurrealRuntimeTruth`` so Agent Brain does not grow a second source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_brain.surrealdb.config import SurrealDbReadSettings
from agent_brain.surrealdb.handoff import StateHandoffDecision
from agent_brain.surrealdb.knowledge_store import SurrealKnowledgeStore
from agent_brain.surrealdb.memory_store import SurrealMemoryStore
from agent_brain.surrealdb.runtime_truth import (
    SurrealRuntimeTruth,
    local_runtime_truth_2026_10_31,
)


def settings_from_runtime_truth(truth: SurrealRuntimeTruth) -> SurrealDbReadSettings:
    """Map frozen inventory facts onto read-adapter settings."""
    # Pin expected major.minor family from verified server version (e.g. 3.0.4 → 3.0).
    parts = truth.server_version.split(".")
    if len(parts) >= 2:
        prefix = f"surrealdb-{parts[0]}.{parts[1]}"
    else:
        prefix = f"surrealdb-{truth.server_version}"
    return SurrealDbReadSettings(
        endpoint="http://127.0.0.1:8010",
        namespace=truth.configured_namespace,
        database=truth.configured_database,
        expected_server_version_prefix=prefix,
    )


@dataclass(frozen=True, slots=True)
class SurrealReadHandoffBundle:
    """One Goal-#67 package: shared truth, stores, and handoff decision."""

    truth: SurrealRuntimeTruth
    settings: SurrealDbReadSettings
    knowledge: SurrealKnowledgeStore
    memory: SurrealMemoryStore
    handoff: StateHandoffDecision

    @property
    def exit_token_ready(self) -> bool:
        """True when handoff is GO and stores share truth-backed settings."""
        return (
            self.handoff.is_go
            and self.settings.namespace == self.truth.configured_namespace
            and self.settings.database == self.truth.configured_database
            and self.knowledge.settings == self.settings
            and self.memory.settings == self.settings
        )


def build_read_handoff_bundle(
    truth: SurrealRuntimeTruth | None = None,
) -> SurrealReadHandoffBundle:
    """Construct the coordinated read + handoff bundle for Goal #67."""
    resolved = truth or local_runtime_truth_2026_10_31()
    settings = settings_from_runtime_truth(resolved)
    return SurrealReadHandoffBundle(
        truth=resolved,
        settings=settings,
        knowledge=SurrealKnowledgeStore(settings),
        memory=SurrealMemoryStore(settings),
        handoff=resolved.handoff_decision(),
    )
