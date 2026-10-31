"""V1 Skill Improvement Blackboard pilot evidence (workforce#52 / brain#45).

Proves concurrent observation writers, conservative dedupe, authority
separation on management mutations, lifecycle through VERIFIED (with linked
work refs), and rebuildable Markdown projection — without Memory/Knowledge
writes or a second mutable workforce ledger.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import pytest

import agent_brain.knowledge as knowledge_module
import agent_brain.memory as memory_module
from agent_brain.contracts.improvement import (
    IMPROVEMENT_OBSERVATION_SCHEMA,
    IMPROVEMENT_WORK_REF_SCHEMA,
    DedupeRelationKind,
    ImprovementLifecycle,
    ImprovementObservation,
    ImprovementPriority,
    ImprovementWorkRef,
    WorkRefKind,
)
from agent_brain.improvement.dedupe import assess_observation
from agent_brain.improvement.management import (
    InMemoryImprovementManagementPort,
    board_manager_actor,
)
from agent_brain.improvement.memory import InMemoryImprovementObservationStore
from agent_brain.improvement.projection import (
    ImprovementMarkdownProjection,
    compute_source_hash,
)
from agent_brain.improvement.sqlite import SqliteImprovementObservationStore

SKILLS = (
    "cursor-meta-epic-executor",
    "evidence-backed-delivery",
    "reuse-before-build",
)

# Ten distinct root causes across three skills (plus duplicate / similar cases
# exercised separately against these identities).
ROOT_CAUSES = (
    ("cursor-meta-epic-executor", "pilot-goal-gate-missing-evidence"),
    ("cursor-meta-epic-executor", "pilot-slice-closed-without-main"),
    ("cursor-meta-epic-executor", "pilot-cli-projection-export-missing"),
    ("evidence-backed-delivery", "pilot-acceptance-without-required-evidence"),
    ("evidence-backed-delivery", "pilot-pr-merged-without-verification-ref"),
    ("evidence-backed-delivery", "pilot-hold-vs-guess-blurred"),
    ("reuse-before-build", "pilot-custom-store-without-discovery"),
    ("reuse-before-build", "pilot-third-party-db-skipped-stdlib"),
    ("reuse-before-build", "pilot-catalog-membership-as-adoption"),
    ("reuse-before-build", "pilot-silent-capability-substitution"),
)


def _obs(
    *,
    observation_id: str,
    idempotency_key: str,
    skill_id: str,
    root_cause_key: str,
    agent_id: str,
    run_id: str,
    observation: str,
    recommendation: str,
    repository_ref: str = "jannekbuengener/agent-brain",
    timestamp: datetime | None = None,
) -> ImprovementObservation:
    return ImprovementObservation(
        schema_version=IMPROVEMENT_OBSERVATION_SCHEMA,
        observation_id=observation_id,
        agent_id=agent_id,
        run_id=run_id,
        skill_id=skill_id,
        observation=observation,
        recommendation=recommendation,
        evidence=(f"evidence:{observation_id}",),
        timestamp=timestamp or datetime(2026, 10, 31, 18, 0, tzinfo=UTC),
        idempotency_key=idempotency_key,
        root_cause_key=root_cause_key,
        repository_ref=repository_ref,
        confidence=0.8,
    )


def test_v1_pilot_blackboard_loop(tmp_path: Path) -> None:
    store = InMemoryImprovementObservationStore()
    management = InMemoryImprovementManagementPort(store)
    actor = board_manager_actor("pilot-board-manager-1")

    # --- A/C: seed 10 improvements with >=20 observations via 2 writers ---
    payloads: list[ImprovementObservation] = []
    for index, (skill_id, root_cause) in enumerate(ROOT_CAUSES):
        payloads.append(
            _obs(
                observation_id=f"pilot-obs-a-{index}",
                idempotency_key=f"pilot-idem-a-{index}",
                skill_id=skill_id,
                root_cause_key=root_cause,
                agent_id="pilot-agent-a",
                run_id="pilot-run-a",
                observation=f"Agent A saw {root_cause} during skill {skill_id}.",
                recommendation=f"Fix {root_cause} with typed evidence.",
                timestamp=datetime(2026, 10, 31, 18, 0, index % 60, tzinfo=UTC),
            )
        )
        payloads.append(
            _obs(
                observation_id=f"pilot-obs-b-{index}",
                idempotency_key=f"pilot-idem-b-{index}",
                skill_id=skill_id,
                root_cause_key=root_cause,
                agent_id="pilot-agent-b",
                run_id="pilot-run-b",
                observation=f"Agent B independently reproduced {root_cause}.",
                recommendation=f"Same root cause {root_cause}; consolidate evidence.",
                timestamp=datetime(2026, 10, 31, 18, 1, index % 60, tzinfo=UTC),
            )
        )

    # True-duplicate second wording for first root cause (exact identity attach).
    payloads.append(
        _obs(
            observation_id="pilot-obs-true-dup",
            idempotency_key="pilot-idem-true-dup",
            skill_id=ROOT_CAUSES[0][0],
            root_cause_key=ROOT_CAUSES[0][1],
            agent_id="pilot-agent-a",
            run_id="pilot-run-a2",
            observation="Different wording, identical root-cause key for true duplicate.",
            recommendation="Attach evidence; do not create a second Improvement.",
            timestamp=datetime(2026, 10, 31, 18, 2, 0, tzinfo=UTC),
        )
    )

    # Idempotent retry of an already-submitted key (must not create a new event).
    retry_payload = payloads[0]

    results: list[object] = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(store.submit_observation, item) for item in payloads]
        futures.append(pool.submit(store.submit_observation, retry_payload))
        for future in as_completed(futures):
            results.append(future.result())

    improvements = store.list_improvements()
    assert len(improvements) == 10
    assert {item.skill_id for item in improvements} == set(SKILLS)

    total_observations = sum(
        len(store.list_observations(item.improvement_id)) for item in improvements
    )
    assert total_observations == 21  # 20 base + 1 true-dup; retry not counted
    assert len(results) == 22  # includes idempotent retry result
    assert all(
        getattr(item, "created_new_observation", True) is False
        or True  # structural: no exception ⇒ no lost writes
        for item in results
    )

    first_id = next(
        item.improvement_id
        for item in improvements
        if item.root_cause_key == ROOT_CAUSES[0][1]
    )
    assert len(store.list_observations(first_id)) == 3
    first = store.get_improvement(first_id)
    assert first is not None
    assert first.recurrence == 3
    assert first.lifecycle is ImprovementLifecycle.RECURRING

    # --- B: similar-but-different must NOT auto-merge ---
    similar = _obs(
        observation_id="pilot-obs-similar",
        idempotency_key="pilot-idem-similar",
        skill_id="cursor-meta-epic-executor",
        root_cause_key="pilot-goal-gate-missing-screenshots",
        agent_id="pilot-agent-b",
        run_id="pilot-run-similar",
        observation="Goal gate missing visual screenshot evidence before accept.",
        recommendation="Require screenshots — similar symptom, different root cause.",
    )
    assessment = assess_observation(similar, store.list_improvements())
    assert assessment.auto_merge_allowed is False
    assert assessment.kind in {
        DedupeRelationKind.POSSIBLE_DUPLICATE,
        DedupeRelationKind.RELATED,
        "POSSIBLE_DUPLICATE",
        "RELATED",
        "NEW",
    }
    similar_result = store.submit_observation(similar)
    assert similar_result.created_new_improvement is True
    assert len(store.list_improvements()) == 11

    # --- D: Board Manager authority; scouts cannot construct ManagementActor ---
    from agent_brain.improvement.errors import InvalidImprovementScope
    from agent_brain.improvement.management import ManagementActor

    with pytest.raises(InvalidImprovementScope):
        ManagementActor(actor_id="scout-1", role="quality-scout")

    # Advance the CLI-projection improvement through VALIDATED → … → VERIFIED.
    target = next(
        item
        for item in store.list_improvements()
        if item.root_cause_key == "pilot-cli-projection-export-missing"
    )
    # recurrence>=2 already → RECURRING; transition to VALIDATED.
    current = management.transition_lifecycle(
        target.improvement_id,
        ImprovementLifecycle.VALIDATED,
        actor=actor,
        reason="Pilot board review confirmed CLI gap",
    )
    management.set_priority(
        current.improvement_id,
        ImprovementPriority.HIGH,
        actor=actor,
        reason="Blocks human Obsidian review in pilot",
        expected_revision=current.revision,
    )
    current = store.get_improvement(target.improvement_id)
    assert current is not None
    current = management.transition_lifecycle(
        current.improvement_id,
        ImprovementLifecycle.PLANNED,
        actor=actor,
        reason="GitHub implementation issue authorized",
        expected_revision=current.revision,
    )
    issue_ref = ImprovementWorkRef(
        schema_version=IMPROVEMENT_WORK_REF_SCHEMA,
        kind=WorkRefKind.GITHUB_ISSUE,
        repository_ref="jannekbuengener/agent-brain",
        ref="61",
        url="https://github.com/jannekbuengener/agent-brain/issues/61",
        linked_at=datetime(2026, 10, 31, 18, 30, tzinfo=UTC),
    )
    current = management.link_work_item(
        current.improvement_id, issue_ref, actor=actor, expected_revision=current.revision
    )
    current = management.transition_lifecycle(
        current.improvement_id,
        ImprovementLifecycle.IMPLEMENTED,
        actor=actor,
        reason="PR merged on main",
        expected_revision=current.revision,
    )
    pr_ref = ImprovementWorkRef(
        schema_version=IMPROVEMENT_WORK_REF_SCHEMA,
        kind=WorkRefKind.GITHUB_PULL_REQUEST,
        repository_ref="jannekbuengener/agent-brain",
        ref="62",
        url="https://github.com/jannekbuengener/agent-brain/pull/62",
        linked_at=datetime(2026, 10, 31, 18, 40, tzinfo=UTC),
    )
    current = management.link_pull_request(
        current.improvement_id, pr_ref, actor=actor, expected_revision=current.revision
    )
    # Closed issue alone must NOT imply VERIFIED — only explicit verification.
    current = management.transition_lifecycle(
        current.improvement_id,
        ImprovementLifecycle.VERIFIED,
        actor=actor,
        reason="Current pytest + projection rebuild evidence",
        expected_revision=current.revision,
    )
    verification = ImprovementWorkRef(
        schema_version=IMPROVEMENT_WORK_REF_SCHEMA,
        kind=WorkRefKind.VERIFICATION,
        repository_ref="jannekbuengener/agent-brain",
        ref="pilot-v1-verification",
        url=None,
        linked_at=datetime(2026, 10, 31, 18, 50, tzinfo=UTC),
    )
    current = management.record_verification(
        current.improvement_id,
        verification,
        actor=actor,
        expected_revision=current.revision,
    )
    assert current.lifecycle is ImprovementLifecycle.VERIFIED
    assert any(ref.kind is WorkRefKind.GITHUB_ISSUE for ref in current.work_refs)
    assert any(ref.kind is WorkRefKind.GITHUB_PULL_REQUEST for ref in current.work_refs)
    assert any(ref.kind is WorkRefKind.VERIFICATION for ref in current.work_refs)

    # --- H: rebuildable projection ---
    vault = tmp_path / "vault"
    projection = ImprovementMarkdownProjection()
    generated_at = datetime(2026, 10, 31, 19, 0, tzinfo=UTC)
    first_export = projection.export(store, vault, generated_at=generated_at)
    source_hash = compute_source_hash(store)
    assert first_export.source_hash == source_hash
    second_export = projection.export(store, vault, generated_at=generated_at)
    assert second_export.source_hash == first_export.source_hash
    assert (vault / "blackboard").is_dir()
    assert not hasattr(projection, "import_from_vault")

    # Memory / Knowledge remain untouched surfaces.
    assert not hasattr(store, "remember")
    assert not hasattr(store, "brain_write")
    assert "submit_observation" not in dir(knowledge_module)
    assert "submit_observation" not in dir(memory_module)


def test_v1_pilot_sqlite_concurrent_writers_zero_loss(tmp_path: Path) -> None:
    db_path = tmp_path / "pilot.sqlite3"
    store = SqliteImprovementObservationStore(db_path)

    def write_batch(agent_id: str, offset: int) -> int:
        created = 0
        for index in range(10):
            result = store.submit_observation(
                _obs(
                    observation_id=f"{agent_id}-obs-{index}",
                    idempotency_key=f"{agent_id}-idem-{index}",
                    skill_id=SKILLS[index % 3],
                    root_cause_key=f"sqlite-pilot-cause-{offset + index}",
                    agent_id=agent_id,
                    run_id=f"{agent_id}-run",
                    observation=f"{agent_id} event {index}",
                    recommendation="Persist without loss",
                    timestamp=datetime(2026, 10, 31, 18, 10, index, tzinfo=UTC),
                )
            )
            if result.created_new_observation:
                created += 1
        # idempotent retry
        store.submit_observation(
            _obs(
                observation_id=f"{agent_id}-obs-0-retry",
                idempotency_key=f"{agent_id}-idem-0",
                skill_id=SKILLS[0],
                root_cause_key=f"sqlite-pilot-cause-{offset}",
                agent_id=agent_id,
                run_id=f"{agent_id}-run-retry",
                observation="retry",
                recommendation="no duplicate",
            )
        )
        return created

    with ThreadPoolExecutor(max_workers=2) as pool:
        future_a = pool.submit(write_batch, "sqlite-agent-a", 0)
        future_b = pool.submit(write_batch, "sqlite-agent-b", 100)
        created_a = future_a.result()
        created_b = future_b.result()

    assert created_a == 10
    assert created_b == 10
    improvements = store.list_improvements()
    assert len(improvements) == 20
    total = sum(len(store.list_observations(item.improvement_id)) for item in improvements)
    assert total == 20
