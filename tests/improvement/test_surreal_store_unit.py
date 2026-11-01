"""Unit-level Surreal Improvement store gates that do not need a live DB."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

import agent_brain.knowledge as knowledge_module
import agent_brain.memory as memory_module
from agent_brain.contracts.improvement import (
    IMPROVEMENT_OBSERVATION_SCHEMA,
    ImprovementObservation,
)
from agent_brain.improvement import (
    ImprovementStoreUnavailable,
    SurrealImprovementObservationStore,
)
from agent_brain.improvement.surreal import SCHEMA_VERSION, surreal_improvement_indexes
from agent_brain.memory.ports import FORBIDDEN_WRITE_METHODS, assert_read_only_store
from agent_brain.surrealdb.config import SurrealDbReadSettings
from agent_brain.surrealdb.http import SurrealHttpProbeResult
from agent_brain.surrealdb.knowledge_store import SurrealKnowledgeStore
from agent_brain.surrealdb.memory_store import SurrealMemoryStore


def _obs(key: str = "k1") -> ImprovementObservation:
    return ImprovementObservation(
        schema_version=IMPROVEMENT_OBSERVATION_SCHEMA,
        observation_id="obs-1",
        agent_id="agent-a",
        run_id="run-1",
        skill_id="cursor-meta-epic-executor",
        observation="mid-layout capture",
        recommendation="require stable geometry",
        evidence=("e1",),
        timestamp=datetime(2026, 10, 31, 12, 0, tzinfo=UTC),
        idempotency_key=key,
        root_cause_key="host-visual-evidence-floor",
    )


def test_surreal_store_unavailable_is_explicit() -> None:
    store = SurrealImprovementObservationStore(available=False, ensure_schema=False)
    with pytest.raises(ImprovementStoreUnavailable):
        store.submit_observation(_obs())


def test_surreal_endpoint_unavailable_fail_closed() -> None:
    def version_prober(endpoint: str, *, timeout_seconds: float) -> SurrealHttpProbeResult:
        _ = endpoint, timeout_seconds
        return SurrealHttpProbeResult(ok=False, error="ConnectionRefusedError: refused")

    store = SurrealImprovementObservationStore(
        SurrealDbReadSettings(endpoint="http://127.0.0.1:1"),
        version_prober=version_prober,
        ensure_schema=False,
    )
    with pytest.raises(ImprovementStoreUnavailable, match="refused|unavailable"):
        store._ensure_schema()


def test_surreal_version_mismatch_fail_closed() -> None:
    def version_prober(endpoint: str, *, timeout_seconds: float) -> SurrealHttpProbeResult:
        _ = endpoint, timeout_seconds
        return SurrealHttpProbeResult(ok=True, status_code=200, body_text="surrealdb-2.6.0")

    store = SurrealImprovementObservationStore(
        SurrealDbReadSettings(expected_server_version_prefix="surrealdb-3.0"),
        version_prober=version_prober,
        ensure_schema=False,
    )
    with pytest.raises(ImprovementStoreUnavailable, match="version mismatch"):
        store._ensure_schema()


def test_surreal_store_has_no_management_methods() -> None:
    store = SurrealImprovementObservationStore(available=False, ensure_schema=False)
    for method_name in SurrealImprovementObservationStore.MANAGEMENT_METHODS:
        assert not hasattr(store, method_name)
    assert not hasattr(store, "remember")
    assert "brain.write" not in dir(store)


def test_read_only_knowledge_memory_boundaries_preserved() -> None:
    knowledge = SurrealKnowledgeStore()
    memory = SurrealMemoryStore()
    assert_read_only_store(knowledge)
    assert_read_only_store(memory)
    for name in FORBIDDEN_WRITE_METHODS:
        assert not hasattr(knowledge, name)
        assert not hasattr(memory, name)
    assert not hasattr(knowledge_module, "write")
    assert not hasattr(memory_module, "write")


def test_schema_and_index_markers_documented() -> None:
    assert SCHEMA_VERSION == "improvement-surreal/v1"
    names = set(surreal_improvement_indexes())
    assert "observation_idempotency_unique" in names
    assert "improvement_id_unique" in names
