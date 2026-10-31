from __future__ import annotations

from datetime import UTC, datetime

import pytest

from agent_brain.contracts.improvement import (
    IMPROVEMENT_OBSERVATION_SCHEMA,
    IMPROVEMENT_WORK_REF_SCHEMA,
    ImprovementLifecycle,
    ImprovementObservation,
    ImprovementPriority,
    ImprovementWorkRef,
    WorkRefKind,
)
from agent_brain.improvement import InMemoryImprovementObservationStore
from agent_brain.improvement.errors import (
    ImprovementValidationError,
    InvalidImprovementScope,
)
from agent_brain.improvement.management import (
    InMemoryImprovementManagementPort,
    ManagementActor,
    board_manager_actor,
    github_issue_work_ref,
)


def _obs(observation_id: str, key: str, root: str = "host-visual-evidence-floor") -> ImprovementObservation:
    return ImprovementObservation(
        schema_version=IMPROVEMENT_OBSERVATION_SCHEMA,
        observation_id=observation_id,
        agent_id="agent-a",
        run_id=f"run-{observation_id}",
        skill_id="cursor-meta-epic-executor",
        observation=f"obs {observation_id}",
        recommendation="fix it",
        evidence=(f"e-{observation_id}",),
        timestamp=datetime(2026, 10, 31, 12, 0, tzinfo=UTC),
        idempotency_key=key,
        root_cause_key=root,
        repository_ref="jannekbuengener/agent-workforce",
    )


def test_observation_store_has_no_management_methods() -> None:
    store = InMemoryImprovementObservationStore()
    for name in (
        "set_priority",
        "transition_lifecycle",
        "merge_improvements",
        "link_work_item",
        "link_pull_request",
        "record_verification",
    ):
        assert not hasattr(store, name)


def test_non_board_manager_actor_denied() -> None:
    with pytest.raises(InvalidImprovementScope):
        ManagementActor(actor_id="scout-1", role="quality-scout")


def test_lifecycle_priority_and_work_link_flow() -> None:
    store = InMemoryImprovementObservationStore()
    store.submit_observation(_obs("obs-1", "k1"))
    store.submit_observation(_obs("obs-2", "k2"))
    mgr = InMemoryImprovementManagementPort(store)
    actor = board_manager_actor("board-1")
    improvement_id = store.list_improvements()[0].improvement_id

    recurring = store.get_improvement(improvement_id)
    assert recurring is not None
    assert recurring.lifecycle is ImprovementLifecycle.RECURRING

    validated = mgr.transition_lifecycle(
        improvement_id,
        ImprovementLifecycle.VALIDATED,
        actor=actor,
        reason="board validated root cause",
        expected_revision=recurring.revision,
    )
    assert validated.lifecycle is ImprovementLifecycle.VALIDATED

    prioritized = mgr.set_priority(
        improvement_id,
        ImprovementPriority.HIGH,
        actor=actor,
        reason="blocks pilot exit",
        expected_revision=validated.revision,
    )
    assert prioritized.priority is ImprovementPriority.HIGH

    planned = mgr.transition_lifecycle(
        improvement_id,
        ImprovementLifecycle.PLANNED,
        actor=actor,
        reason="owner repo clear",
    )
    linked = mgr.link_work_item(
        improvement_id,
        github_issue_work_ref(
            repository_ref="jannekbuengener/agent-workforce",
            issue_number="999",
            url="https://github.com/jannekbuengener/agent-workforce/issues/999",
            linked_at=datetime(2026, 10, 31, 16, 0, tzinfo=UTC),
        ),
        actor=actor,
        expected_revision=planned.revision,
    )
    assert any(ref.kind is WorkRefKind.GITHUB_ISSUE and ref.ref == "999" for ref in linked.work_refs)

    # idempotent link
    again = mgr.link_work_item(
        improvement_id,
        github_issue_work_ref(
            repository_ref="jannekbuengener/agent-workforce",
            issue_number="999",
        ),
        actor=actor,
    )
    assert len([ref for ref in again.work_refs if ref.ref == "999"]) == 1


def test_illegal_lifecycle_transition_rejected() -> None:
    store = InMemoryImprovementObservationStore()
    store.submit_observation(_obs("obs-1", "k1"))
    mgr = InMemoryImprovementManagementPort(store)
    improvement_id = store.list_improvements()[0].improvement_id
    with pytest.raises(ValueError, match="illegal lifecycle transition"):
        mgr.transition_lifecycle(
            improvement_id,
            ImprovementLifecycle.VERIFIED,
            actor=board_manager_actor("board-1"),
            reason="skip ahead",
        )


def test_revision_conflict_and_merge_lineage() -> None:
    store = InMemoryImprovementObservationStore()
    store.submit_observation(_obs("obs-1", "k1", root="host-visual-evidence-floor"))
    store.submit_observation(
        _obs("obs-2", "k2", root="host-visual-evidence-floor-alias")
    )
    mgr = InMemoryImprovementManagementPort(store)
    actor = board_manager_actor("board-1")
    target_id = "improvement:cursor-meta-epic-executor:host-visual-evidence-floor"
    source_id = "improvement:cursor-meta-epic-executor:host-visual-evidence-floor-alias"
    target = store.get_improvement(target_id)
    assert target is not None

    with pytest.raises(ImprovementValidationError, match="revision conflict"):
        mgr.set_priority(
            target_id,
            ImprovementPriority.LOW,
            actor=actor,
            reason="stale",
            expected_revision=target.revision + 99,
        )

    merged = mgr.merge_improvements(
        target_id,
        [source_id],
        actor=actor,
        reason="exact identity confirmed",
        evidence=["board-review"],
        merge_id="merge-1",
        merged_at=datetime(2026, 10, 31, 16, 30, tzinfo=UTC),
    )
    assert source_id in merged.aliases
    assert merged.merge_lineage[-1].merge_id == "merge-1"
    assert merged.recurrence == 2
    superseded = store.get_improvement(source_id)
    assert superseded is not None
    assert superseded.superseded_by_improvement_id == target_id


def test_record_verification_requires_verification_kind() -> None:
    store = InMemoryImprovementObservationStore()
    store.submit_observation(_obs("obs-1", "k1"))
    store.submit_observation(_obs("obs-2", "k2"))
    mgr = InMemoryImprovementManagementPort(store)
    actor = board_manager_actor("board-1")
    improvement_id = store.list_improvements()[0].improvement_id
    mgr.transition_lifecycle(
        improvement_id, ImprovementLifecycle.VALIDATED, actor=actor, reason="ok"
    )
    mgr.transition_lifecycle(
        improvement_id, ImprovementLifecycle.PLANNED, actor=actor, reason="ok"
    )
    mgr.transition_lifecycle(
        improvement_id, ImprovementLifecycle.IMPLEMENTED, actor=actor, reason="ok"
    )
    with pytest.raises(ImprovementValidationError, match="work_ref.kind"):
        mgr.record_verification(
            improvement_id,
            ImprovementWorkRef(
                schema_version=IMPROVEMENT_WORK_REF_SCHEMA,
                kind=WorkRefKind.GITHUB_ISSUE,
                repository_ref="jannekbuengener/agent-workforce",
                ref="1",
            ),
            actor=actor,
        )
    verified_ref = ImprovementWorkRef(
        schema_version=IMPROVEMENT_WORK_REF_SCHEMA,
        kind=WorkRefKind.VERIFICATION,
        repository_ref="jannekbuengener/agent-workforce",
        ref="verify-1",
    )
    linked = mgr.record_verification(improvement_id, verified_ref, actor=actor)
    assert any(ref.kind is WorkRefKind.VERIFICATION for ref in linked.work_refs)
    done = mgr.transition_lifecycle(
        improvement_id,
        ImprovementLifecycle.VERIFIED,
        actor=actor,
        reason="current verification attached",
    )
    assert done.lifecycle is ImprovementLifecycle.VERIFIED
