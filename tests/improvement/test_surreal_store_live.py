"""Live SurrealDB acceptance for SurrealImprovementObservationStore (#64/#89).

Requires an isolated SurrealDB 3.0.x endpoint. Prefer disposable scratch runtimes;
never attach unknown Claire/production volumes.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from agent_brain.contracts.improvement import (
    IMPROVEMENT_OBSERVATION_SCHEMA,
    IMPROVEMENT_WORK_REF_SCHEMA,
    ImprovementLifecycle,
    ImprovementObservation,
    ImprovementPriority,
    ImprovementWorkRef,
    WorkRefKind,
    build_improvement_id,
)
from agent_brain.contracts.serialization import serialize_contract
from agent_brain.improvement import (
    ImprovementMarkdownProjection,
    ImprovementStoreUnavailable,
    ImprovementValidationError,
    SurrealImprovementManagementPort,
    SurrealImprovementObservationStore,
    board_manager_actor,
)
from agent_brain.surrealdb.config import SurrealDbReadSettings
from agent_brain.surrealdb.http import probe_version

SURREAL_ENDPOINT = os.environ.get("AGENT_BRAIN_SURREAL_ENDPOINT", "http://127.0.0.1:8010")
SURREAL_DIGEST = (
    "sha256:65000ff205b08363b035b457f292dc0a0b1cd4212935dd5ea94073cf67adf306"
)


def _surreal_reachable(endpoint: str) -> bool:
    probe = probe_version(endpoint, timeout_seconds=1.0)
    return bool(probe.ok and probe.version_text and probe.version_text.startswith("surrealdb-3.0"))


pytestmark = pytest.mark.skipif(
    not _surreal_reachable(SURREAL_ENDPOINT),
    reason=(
        f"SurrealDB 3.0 endpoint not reachable at {SURREAL_ENDPOINT}; "
        "start an isolated scratch runtime to run live #64/#89 acceptance"
    ),
)


def _settings(database: str) -> SurrealDbReadSettings:
    return SurrealDbReadSettings(
        endpoint=SURREAL_ENDPOINT,
        namespace="agent_brain_89",
        database=database,
        timeout_seconds=5.0,
        expected_server_version_prefix="surrealdb-3.0",
    )


def _observation(
    *,
    observation_id: str,
    idempotency_key: str,
    agent_id: str = "agent-a",
    timestamp: datetime | None = None,
    observation: str = "Capture happened mid-layout.",
    root_cause_key: str = "host-visual-evidence-floor",
) -> ImprovementObservation:
    return ImprovementObservation(
        schema_version=IMPROVEMENT_OBSERVATION_SCHEMA,
        observation_id=observation_id,
        agent_id=agent_id,
        run_id=f"run-{observation_id}",
        skill_id="cursor-meta-epic-executor",
        observation=observation,
        recommendation="Require stable geometry before acceptance.",
        evidence=(f"evidence:{observation_id}",),
        timestamp=timestamp or datetime(2026, 10, 31, 12, 0, tzinfo=UTC),
        idempotency_key=idempotency_key,
        root_cause_key=root_cause_key,
        repository_ref="jannekbuengener/agent-workforce",
        confidence=0.7,
    )


@pytest.fixture()
def store() -> SurrealImprovementObservationStore:
    # Unique DB per test for isolation on shared scratch server.
    db_name = f"imp_{uuid.uuid4().hex}"
    return SurrealImprovementObservationStore(_settings(db_name))


def test_live_contract_parity_create_retry_list(store: SurrealImprovementObservationStore) -> None:
    first = store.submit_observation(_observation(observation_id="obs-1", idempotency_key="k1"))
    assert first.created_new_improvement is True
    assert first.created_new_observation is True
    assert first.improvement.recurrence == 1

    retry = store.submit_observation(_observation(observation_id="obs-1", idempotency_key="k1"))
    assert retry.created_new_observation is False
    assert len(store.list_observations(first.improvement.improvement_id)) == 1

    second = store.submit_observation(
        _observation(
            observation_id="obs-2",
            idempotency_key="k2",
            agent_id="agent-b",
            timestamp=datetime(2026, 10, 31, 12, 5, tzinfo=UTC),
        )
    )
    assert second.created_new_improvement is False
    assert second.improvement.recurrence == 2
    assert second.improvement.lifecycle is ImprovementLifecycle.RECURRING
    assert store.get_improvement(first.improvement.improvement_id) is not None
    assert len(store.list_improvements(skill_id="cursor-meta-epic-executor")) == 1


def test_live_parallel_writers_and_retry(
    store: SurrealImprovementObservationStore,
) -> None:
    base = datetime(2026, 10, 31, 15, 0, tzinfo=UTC)

    def write(index: int) -> str:
        # Each worker also retries once to prove idempotent retry under load.
        payload = _observation(
            observation_id=f"obs-{index}",
            idempotency_key=f"parallel-{index}",
            agent_id="writer-a" if index % 2 == 0 else "writer-b",
            timestamp=base + timedelta(seconds=index),
            observation=f"Parallel observation {index}",
        )
        first = store.submit_observation(payload)
        retry = store.submit_observation(payload)
        assert retry.created_new_observation is False
        assert first.observation.observation_id == retry.observation.observation_id
        return first.observation.observation_id

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(write, i) for i in range(20)]
        ids = [future.result() for future in as_completed(futures)]

    assert len(ids) == 20
    assert len(set(ids)) == 20
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


def test_live_aggregate_rebuild_and_projection(
    store: SurrealImprovementObservationStore,
    tmp_path: Path,
) -> None:
    store.submit_observation(_observation(observation_id="obs-1", idempotency_key="k1"))
    store.submit_observation(
        _observation(
            observation_id="obs-2",
            idempotency_key="k2",
            timestamp=datetime(2026, 10, 31, 12, 1, tzinfo=UTC),
        )
    )
    improvement_id = build_improvement_id(
        skill_id="cursor-meta-epic-executor",
        root_cause_key="host-visual-evidence-floor",
    )
    rebuilt = store._refresh_aggregate(improvement_id)
    assert rebuilt.recurrence == 2
    assert rebuilt.lifecycle is ImprovementLifecycle.RECURRING

    projection = ImprovementMarkdownProjection()
    result = projection.export(
        store,
        tmp_path / "projection",
        generated_at=datetime(2026, 11, 1, 12, 0, tzinfo=UTC),
    )
    assert result.files_written
    exported = list((tmp_path / "projection").rglob("*.md"))
    assert exported


def test_live_management_revision_and_capability_gates(
    store: SurrealImprovementObservationStore,
) -> None:
    store.submit_observation(_observation(observation_id="obs-1", idempotency_key="k1"))
    store.submit_observation(
        _observation(
            observation_id="obs-2",
            idempotency_key="k2",
            timestamp=datetime(2026, 10, 31, 12, 2, tzinfo=UTC),
        )
    )
    mgr = SurrealImprovementManagementPort(store)
    actor = board_manager_actor("board-1")
    improvement_id = store.list_improvements()[0].improvement_id
    current = store.get_improvement(improvement_id)
    assert current is not None

    with pytest.raises(ImprovementValidationError, match="revision conflict"):
        mgr.set_priority(
            improvement_id,
            ImprovementPriority.HIGH,
            actor=actor,
            reason="stale",
            expected_revision=current.revision - 1 if current.revision > 0 else 999_999,
        )

    validated = mgr.transition_lifecycle(
        improvement_id,
        ImprovementLifecycle.VALIDATED,
        actor=actor,
        reason="board validated",
        expected_revision=current.revision,
    )
    assert validated.lifecycle is ImprovementLifecycle.VALIDATED
    linked = mgr.link_work_item(
        improvement_id,
        ImprovementWorkRef(
            schema_version=IMPROVEMENT_WORK_REF_SCHEMA,
            kind=WorkRefKind.GITHUB_ISSUE,
            repository_ref="jannekbuengener/agent-brain",
            ref="64",
        ),
        actor=actor,
        expected_revision=validated.revision,
    )
    assert any(ref.ref == "64" for ref in linked.work_refs)


def test_live_backup_restore_parity_after_parallel_writes(
    store: SurrealImprovementObservationStore,
    tmp_path: Path,
) -> None:
    base = datetime(2026, 10, 31, 16, 0, tzinfo=UTC)

    def write(index: int) -> None:
        store.submit_observation(
            _observation(
                observation_id=f"obs-{index}",
                idempotency_key=f"bak-{index}",
                agent_id="writer-a" if index % 2 == 0 else "writer-b",
                timestamp=base + timedelta(milliseconds=index),
                observation=f"Backup observation {index}",
            )
        )

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(write, range(12)))

    snapshot = store.export_board_snapshot()
    artifact = tmp_path / "improvement_board_export.json"
    encoded = serialize_contract(snapshot)
    artifact.write_text(encoded, encoding="utf-8")
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    assert snapshot["counts"]["observations"] == 12
    assert digest

    target = SurrealImprovementObservationStore(_settings(f"restore_{uuid.uuid4().hex}"))
    target.import_board_snapshot(json.loads(artifact.read_text(encoding="utf-8")))

    source_ids = {
        item.observation_id
        for item in store.list_observations(store.list_improvements()[0].improvement_id)
    }
    target_ids = {
        item.observation_id
        for item in target.list_observations(target.list_improvements()[0].improvement_id)
    }
    assert source_ids == target_ids
    assert len(source_ids) == 12
    src_imp = store.list_improvements()[0]
    dst_imp = target.list_improvements()[0]
    assert src_imp.improvement_id == dst_imp.improvement_id
    assert src_imp.recurrence == dst_imp.recurrence
    assert src_imp.root_cause_key == dst_imp.root_cause_key
    # Import into non-empty must fail closed.
    with pytest.raises(ImprovementValidationError, match="non-empty"):
        target.import_board_snapshot(snapshot)


def test_live_backend_loss_is_unavailable_not_empty(
    store: SurrealImprovementObservationStore,
) -> None:
    store.submit_observation(_observation(observation_id="obs-1", idempotency_key="k1"))
    store.mark_unavailable()
    with pytest.raises(ImprovementStoreUnavailable):
        store.list_improvements()
    with pytest.raises(ImprovementStoreUnavailable):
        store.submit_observation(_observation(observation_id="obs-2", idempotency_key="k2"))
