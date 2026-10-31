from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from agent_brain.contracts.improvement import (
    IMPROVEMENT_OBSERVATION_SCHEMA,
    ImprovementLifecycle,
    ImprovementObservation,
    build_improvement_id,
)
from agent_brain.improvement import (
    ImprovementIdentityAmbiguous,
    ImprovementStoreUnavailable,
    InMemoryImprovementObservationStore,
    SqliteImprovementObservationStore,
)


def _observation(
    *,
    observation_id: str,
    idempotency_key: str,
    agent_id: str = "agent-a",
    timestamp: datetime | None = None,
    observation: str = "Capture happened mid-layout.",
) -> ImprovementObservation:
    return ImprovementObservation(
        schema_version=IMPROVEMENT_OBSERVATION_SCHEMA,
        observation_id=observation_id,
        agent_id=agent_id,
        run_id=f"run-{observation_id}",
        skill_id="cursor-meta-epic-executor",
        observation=observation,
        recommendation="Require stable geometry before acceptance.",
        evidence=[f"evidence:{observation_id}"],
        timestamp=timestamp or datetime(2026, 10, 31, 12, 0, tzinfo=UTC),
        idempotency_key=idempotency_key,
        root_cause_key="host-visual-evidence-floor",
        repository_ref="jannekbuengener/agent-workforce",
        confidence=0.7,
    )


def test_sqlite_persists_across_reopen(tmp_path: Path) -> None:
    db_path = tmp_path / "improvements.sqlite3"
    store = SqliteImprovementObservationStore(db_path)
    first = store.submit_observation(_observation(observation_id="obs-1", idempotency_key="k1"))
    improvement_id = first.improvement.improvement_id

    reopened = SqliteImprovementObservationStore(db_path)
    loaded = reopened.get_improvement(improvement_id)
    assert loaded is not None
    assert loaded.recurrence == 1
    assert len(reopened.list_observations(improvement_id)) == 1

    retry = reopened.submit_observation(
        _observation(observation_id="obs-1", idempotency_key="k1")
    )
    assert retry.created_new_observation is False
    assert len(reopened.list_observations(improvement_id)) == 1


def test_sqlite_parallel_writers_and_derived_recurrence(tmp_path: Path) -> None:
    store = SqliteImprovementObservationStore(tmp_path / "improvements.sqlite3")
    base = datetime(2026, 10, 31, 14, 0, tzinfo=UTC)

    def write(index: int) -> str:
        result = store.submit_observation(
            _observation(
                observation_id=f"obs-{index}",
                idempotency_key=f"parallel-{index}",
                agent_id=f"agent-{index % 2}",
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
    improvement = store.get_improvement(improvement_id)
    assert improvement is not None
    assert improvement.recurrence == 20
    assert improvement.lifecycle is ImprovementLifecycle.RECURRING


def test_sqlite_unavailable_and_ambiguous_identity(tmp_path: Path) -> None:
    store = SqliteImprovementObservationStore(tmp_path / "improvements.sqlite3", available=False)
    with pytest.raises(ImprovementStoreUnavailable):
        store.submit_observation(_observation(observation_id="obs-1", idempotency_key="k1"))

    available = SqliteImprovementObservationStore(tmp_path / "improvements.sqlite3")
    bare = ImprovementObservation(
        schema_version=IMPROVEMENT_OBSERVATION_SCHEMA,
        observation_id="obs-x",
        agent_id="a",
        run_id="r",
        skill_id="cursor-meta-epic-executor",
        observation="x",
        recommendation="y",
        evidence=("e",),
        timestamp=datetime(2026, 10, 31, 12, 0, tzinfo=UTC),
        idempotency_key="amb",
    )
    with pytest.raises(ImprovementIdentityAmbiguous):
        available.submit_observation(bare)


def test_sqlite_has_no_management_methods(tmp_path: Path) -> None:
    store = SqliteImprovementObservationStore(tmp_path / "improvements.sqlite3")
    for method_name in SqliteImprovementObservationStore.MANAGEMENT_METHODS:
        assert not hasattr(store, method_name)
    assert InMemoryImprovementObservationStore.MANAGEMENT_METHODS == (
        SqliteImprovementObservationStore.MANAGEMENT_METHODS
    )
