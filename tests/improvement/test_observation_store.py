from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta

import pytest

import agent_brain.knowledge as knowledge_module
import agent_brain.memory as memory_module
from agent_brain.contracts.improvement import (
    IMPROVEMENT_OBSERVATION_SCHEMA,
    ImprovementLifecycle,
    ImprovementObservation,
    build_improvement_id,
)
from agent_brain.improvement import (
    ImprovementIdentityAmbiguous,
    ImprovementStoreUnavailable,
    ImprovementValidationError,
    InMemoryImprovementObservationStore,
    InvalidImprovementScope,
)


def _observation(
    *,
    observation_id: str,
    idempotency_key: str,
    agent_id: str = "agent-a",
    run_id: str = "run-1",
    skill_id: str = "cursor-meta-epic-executor",
    root_cause_key: str = "host-visual-evidence-floor",
    timestamp: datetime | None = None,
    repository_ref: str | None = "jannekbuengener/agent-workforce",
    observation: str = "Capture happened mid-layout.",
    recommendation: str = "Require stable geometry before acceptance.",
) -> ImprovementObservation:
    return ImprovementObservation(
        schema_version=IMPROVEMENT_OBSERVATION_SCHEMA,
        observation_id=observation_id,
        agent_id=agent_id,
        run_id=run_id,
        skill_id=skill_id,
        observation=observation,
        recommendation=recommendation,
        evidence=[f"evidence:{observation_id}"],
        timestamp=timestamp or datetime(2026, 10, 31, 12, 0, tzinfo=UTC),
        idempotency_key=idempotency_key,
        root_cause_key=root_cause_key,
        repository_ref=repository_ref,
        confidence=0.7,
    )


def test_submit_observation_creates_improvement_and_derives_recurrence() -> None:
    store = InMemoryImprovementObservationStore()
    first = store.submit_observation(_observation(observation_id="obs-1", idempotency_key="k1"))
    assert first.created_new_improvement is True
    assert first.created_new_observation is True
    assert first.improvement.recurrence == 1
    assert first.improvement.lifecycle is ImprovementLifecycle.NEW

    second = store.submit_observation(
        _observation(
            observation_id="obs-2",
            idempotency_key="k2",
            agent_id="agent-b",
            timestamp=datetime(2026, 10, 31, 12, 5, tzinfo=UTC),
            observation="Same root cause, different wording.",
        )
    )
    assert second.created_new_improvement is False
    assert second.improvement.recurrence == 2
    assert second.improvement.lifecycle is ImprovementLifecycle.RECURRING
    assert second.improvement.improvement_id == build_improvement_id(
        skill_id="cursor-meta-epic-executor",
        root_cause_key="host-visual-evidence-floor",
    )
    assert len(store.list_observations(second.improvement.improvement_id)) == 2


def test_submit_observation_is_idempotent_on_retry() -> None:
    store = InMemoryImprovementObservationStore()
    payload = _observation(observation_id="obs-1", idempotency_key="retry-key")
    first = store.submit_observation(payload)
    retry = store.submit_observation(payload)
    assert retry.created_new_observation is False
    assert retry.observation == first.observation
    assert retry.improvement.improvement_id == first.improvement.improvement_id
    assert len(store.list_observations(first.improvement.improvement_id)) == 1
    assert first.improvement.recurrence == 1


def test_parallel_writers_lose_zero_events() -> None:
    store = InMemoryImprovementObservationStore()
    base = datetime(2026, 10, 31, 13, 0, tzinfo=UTC)

    def write(index: int) -> str:
        result = store.submit_observation(
            _observation(
                observation_id=f"obs-{index}",
                idempotency_key=f"parallel-{index}",
                agent_id=f"agent-{index % 2}",
                run_id=f"run-{index}",
                timestamp=base + timedelta(seconds=index),
                observation=f"Parallel observation {index}",
            )
        )
        return result.observation.observation_id

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(write, i) for i in range(20)]
        ids = [future.result() for future in as_completed(futures)]

    assert len(ids) == 20
    improvement_id = build_improvement_id(
        skill_id="cursor-meta-epic-executor",
        root_cause_key="host-visual-evidence-floor",
    )
    history = store.list_observations(improvement_id)
    assert len(history) == 20
    assert {item.observation_id for item in history} == {f"obs-{i}" for i in range(20)}
    improvement = store.get_improvement(improvement_id)
    assert improvement is not None
    assert improvement.recurrence == 20
    assert improvement.lifecycle is ImprovementLifecycle.RECURRING


def test_parallel_idempotent_retries_do_not_duplicate() -> None:
    store = InMemoryImprovementObservationStore()
    payload = _observation(observation_id="obs-dup", idempotency_key="shared-retry")

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(store.submit_observation, payload) for _ in range(12)]
        results = [future.result() for future in as_completed(futures)]

    assert len(results) == 12
    assert sum(1 for item in results if item.created_new_observation) == 1
    improvement_id = results[0].improvement.improvement_id
    assert len(store.list_observations(improvement_id)) == 1


def test_unavailable_backend_fails_closed() -> None:
    store = InMemoryImprovementObservationStore(available=False)
    with pytest.raises(ImprovementStoreUnavailable):
        store.submit_observation(_observation(observation_id="obs-1", idempotency_key="k1"))


def test_ambiguous_identity_fails_closed() -> None:
    store = InMemoryImprovementObservationStore()
    payload = _observation(observation_id="obs-1", idempotency_key="k1")
    payload = ImprovementObservation(
        schema_version=payload.schema_version,
        observation_id=payload.observation_id,
        agent_id=payload.agent_id,
        run_id=payload.run_id,
        skill_id=payload.skill_id,
        observation=payload.observation,
        recommendation=payload.recommendation,
        evidence=payload.evidence,
        timestamp=payload.timestamp,
        idempotency_key=payload.idempotency_key,
        root_cause_key=None,
        improvement_id=None,
    )
    with pytest.raises(ImprovementIdentityAmbiguous):
        store.submit_observation(payload)


def test_mismatched_improvement_id_and_root_cause_rejected() -> None:
    store = InMemoryImprovementObservationStore()
    payload = _observation(observation_id="obs-1", idempotency_key="k1")
    bad = ImprovementObservation(
        schema_version=payload.schema_version,
        observation_id=payload.observation_id,
        agent_id=payload.agent_id,
        run_id=payload.run_id,
        skill_id=payload.skill_id,
        observation=payload.observation,
        recommendation=payload.recommendation,
        evidence=payload.evidence,
        timestamp=payload.timestamp,
        idempotency_key=payload.idempotency_key,
        root_cause_key=payload.root_cause_key,
        improvement_id="improvement:other-skill:other-cause",
    )
    with pytest.raises(InvalidImprovementScope):
        store.submit_observation(bad)


def test_observation_writer_has_no_management_methods() -> None:
    store = InMemoryImprovementObservationStore()
    for method_name in InMemoryImprovementObservationStore.MANAGEMENT_METHODS:
        assert not hasattr(store, method_name)


def test_list_and_find_candidates_filter_by_skill_and_repo() -> None:
    store = InMemoryImprovementObservationStore()
    store.submit_observation(_observation(observation_id="obs-1", idempotency_key="k1"))
    store.submit_observation(
        _observation(
            observation_id="obs-other",
            idempotency_key="k-other",
            skill_id="evidence-backed-delivery",
            root_cause_key="missing-locator-kind",
            repository_ref="jannekbuengener/agent-brain",
        )
    )
    listed = store.list_improvements(skill_id="cursor-meta-epic-executor")
    assert len(listed) == 1
    candidates = store.find_candidates(
        skill_id="cursor-meta-epic-executor",
        root_cause_key="host-visual-evidence-floor",
    )
    assert len(candidates) == 1
    assert store.find_candidates(skill_id="missing-skill") == ()


def test_duplicate_observation_id_with_new_idempotency_key_rejected() -> None:
    store = InMemoryImprovementObservationStore()
    store.submit_observation(_observation(observation_id="obs-1", idempotency_key="k1"))
    with pytest.raises(ImprovementValidationError, match="observation_id already exists"):
        store.submit_observation(_observation(observation_id="obs-1", idempotency_key="k2"))


def test_memory_and_knowledge_modules_remain_without_generic_write_api() -> None:
    assert not hasattr(memory_module, "remember")
    assert not hasattr(memory_module, "MemoryStore")
    assert not hasattr(knowledge_module, "KnowledgeStore")
    assert not hasattr(knowledge_module, "write")
    assert not hasattr(InMemoryImprovementObservationStore, "remember")
    assert "brain.write" not in dir(InMemoryImprovementObservationStore)
