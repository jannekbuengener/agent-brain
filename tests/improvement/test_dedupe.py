from __future__ import annotations

from datetime import UTC, datetime

from agent_brain.contracts.improvement import (
    IMPROVEMENT_OBSERVATION_SCHEMA,
    IMPROVEMENT_SCHEMA,
    DedupeRelationKind,
    Improvement,
    ImprovementLifecycle,
    ImprovementObservation,
)
from agent_brain.improvement.dedupe import (
    assess_observation,
    merge_improvements,
    relate_improvements,
)


def _improvement(
    *,
    skill_id: str,
    root_cause_key: str,
    summary: str,
    recommendation: str,
) -> Improvement:
    improvement_id = f"improvement:{skill_id}:{root_cause_key}"
    return Improvement(
        schema_version=IMPROVEMENT_SCHEMA,
        improvement_id=improvement_id,
        skill_id=skill_id,
        root_cause_key=root_cause_key,
        summary=summary,
        recommendation=recommendation,
        expected_benefit="benefit",
        lifecycle=ImprovementLifecycle.NEW,
        first_seen=datetime(2026, 10, 30, 10, 0, tzinfo=UTC),
        last_seen=datetime(2026, 10, 30, 10, 0, tzinfo=UTC),
        recurrence=1,
    )


def _observation(
    *,
    root_cause_key: str | None,
    observation: str,
    recommendation: str,
    skill_id: str = "cursor-meta-epic-executor",
) -> ImprovementObservation:
    return ImprovementObservation(
        schema_version=IMPROVEMENT_OBSERVATION_SCHEMA,
        observation_id="obs-1",
        agent_id="agent-a",
        run_id="run-1",
        skill_id=skill_id,
        observation=observation,
        recommendation=recommendation,
        evidence=("e1",),
        timestamp=datetime(2026, 10, 31, 12, 0, tzinfo=UTC),
        idempotency_key="k1",
        root_cause_key=root_cause_key,
    )


def test_exact_identity_true_duplicate_allows_auto_attach() -> None:
    existing = _improvement(
        skill_id="cursor-meta-epic-executor",
        root_cause_key="host-visual-evidence-floor",
        summary="Screenshots taken before layout settled.",
        recommendation="Wait for stable geometry.",
    )
    observation = _observation(
        root_cause_key="Host Visual Evidence Floor",
        observation="Different wording for the same root cause.",
        recommendation="Gate visual acceptance on stable geometry.",
    )
    assessment = assess_observation(observation, [existing])
    assert assessment.kind is DedupeRelationKind.EXACT_IDENTITY
    assert assessment.auto_merge_allowed is True
    assert assessment.target_improvement_id == existing.improvement_id


def test_similar_but_different_does_not_auto_merge() -> None:
    existing = _improvement(
        skill_id="cursor-meta-epic-executor",
        root_cause_key="host-visual-evidence-floor",
        summary="Screenshots taken before layout settled for visual acceptance.",
        recommendation="Wait for stable geometry before visual acceptance screenshots.",
    )
    observation = _observation(
        root_cause_key="owner-visual-self-pass-forbidden",
        observation="Screenshots taken before layout settled for visual acceptance.",
        recommendation="Wait for stable geometry before visual acceptance screenshots.",
    )
    assessment = assess_observation(observation, [existing])
    assert assessment.kind is DedupeRelationKind.POSSIBLE_DUPLICATE
    assert assessment.auto_merge_allowed is False
    assert assessment.target_improvement_id == existing.improvement_id
    assert any(signal.name == "auto_merge_blocked" for signal in assessment.signals)


def test_weak_similarity_marks_related_not_merge() -> None:
    existing = _improvement(
        skill_id="cursor-meta-epic-executor",
        root_cause_key="host-visual-evidence-floor",
        summary="Screenshots taken before layout settled.",
        recommendation="Wait for stable geometry.",
    )
    observation = _observation(
        root_cause_key="merge-order-unclear-hold",
        observation="Dependency merge order is unclear across PRs.",
        recommendation="HOLD until merge order is explicit.",
    )
    assessment = assess_observation(observation, [existing])
    assert assessment.kind in {DedupeRelationKind.RELATED, "NEW"}
    assert assessment.auto_merge_allowed is False


def test_merge_improvements_preserves_lineage_and_supersession() -> None:
    target = _improvement(
        skill_id="cursor-meta-epic-executor",
        root_cause_key="host-visual-evidence-floor",
        summary="Primary record",
        recommendation="Stable geometry gate",
    )
    source = _improvement(
        skill_id="cursor-meta-epic-executor",
        root_cause_key="host-visual-evidence-floor-alias",
        summary="Duplicate wording record",
        recommendation="Stable geometry gate",
    )
    merged, superseded, lineage = merge_improvements(
        target=target,
        sources=[source],
        actor_id="improvement-board-manager",
        reason="exact identity confirmed by board",
        evidence=["exact-root-cause-review"],
        merged_at=datetime(2026, 10, 31, 15, 0, tzinfo=UTC),
        merge_id="merge-1",
    )
    assert lineage.target_improvement_id == target.improvement_id
    assert source.improvement_id in merged.aliases
    assert merged.merge_lineage[-1] == lineage
    assert superseded[0].superseded_by_improvement_id == target.improvement_id


def test_relate_improvements_does_not_collapse_identity() -> None:
    left = _improvement(
        skill_id="cursor-meta-epic-executor",
        root_cause_key="host-visual-evidence-floor",
        summary="A",
        recommendation="A",
    )
    right = _improvement(
        skill_id="cursor-meta-epic-executor",
        root_cause_key="owner-visual-self-pass-forbidden",
        summary="B",
        recommendation="B",
    )
    related_left, related_right = relate_improvements(
        left,
        right,
        kind=DedupeRelationKind.POSSIBLE_DUPLICATE,
        reason="similar symptoms, different root cause",
    )
    assert related_left.improvement_id != related_right.improvement_id
    assert related_left.relations[0].kind is DedupeRelationKind.POSSIBLE_DUPLICATE
    assert related_left.superseded_by_improvement_id is None
