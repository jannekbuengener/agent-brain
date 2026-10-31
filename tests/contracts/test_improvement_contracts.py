from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone

import pytest

from agent_brain.contracts.improvement import (
    ALLOWED_LIFECYCLE_TRANSITIONS,
    IMPROVEMENT_MERGE_LINEAGE_SCHEMA,
    IMPROVEMENT_OBSERVATION_SCHEMA,
    IMPROVEMENT_SCHEMA,
    IMPROVEMENT_WORK_REF_SCHEMA,
    DedupeRelationKind,
    Improvement,
    ImprovementLifecycle,
    ImprovementMergeLineage,
    ImprovementObservation,
    ImprovementPriority,
    ImprovementRelation,
    ImprovementWorkRef,
    WorkRefKind,
    build_improvement_id,
    derive_recurrence,
    is_lifecycle_transition_allowed,
    normalize_root_cause_key,
    require_lifecycle_transition,
)
from agent_brain.contracts.provenance import Provenance
from agent_brain.contracts.registry import CONTRACT_SCHEMAS
from agent_brain.contracts.resolution import ResolutionMeta
from agent_brain.contracts.serialization import serialize_contract
from agent_brain.contracts.temporal import TemporalEnvelope


def _base_improvement(**overrides: object) -> Improvement:
    payload = {
        "schema_version": IMPROVEMENT_SCHEMA,
        "improvement_id": "improvement:cursor-meta-epic-executor:host-visual-evidence-floor",
        "skill_id": "cursor-meta-epic-executor",
        "root_cause_key": "host-visual-evidence-floor",
        "summary": "Host visual acceptance captured before geometry was stable.",
        "recommendation": "Require stable geometry before acceptance screenshots.",
        "expected_benefit": "Fewer false visual PASS/FAIL decisions.",
        "lifecycle": ImprovementLifecycle.NEW,
        "first_seen": datetime(2026, 10, 30, 10, 0, tzinfo=UTC),
        "last_seen": datetime(2026, 10, 30, 10, 0, tzinfo=UTC),
        "recurrence": 1,
        "confidence": 0.8,
        "priority": ImprovementPriority.HIGH,
    }
    payload.update(overrides)
    return Improvement(**payload)  # type: ignore[arg-type]


def test_registry_exposes_improvement_schemas() -> None:
    assert CONTRACT_SCHEMAS["improvement"] == IMPROVEMENT_SCHEMA
    assert CONTRACT_SCHEMAS["improvement-observation"] == IMPROVEMENT_OBSERVATION_SCHEMA
    assert CONTRACT_SCHEMAS["improvement-merge-lineage"] == IMPROVEMENT_MERGE_LINEAGE_SCHEMA
    assert CONTRACT_SCHEMAS["improvement-work-ref"] == IMPROVEMENT_WORK_REF_SCHEMA


def test_normalize_root_cause_key_is_deterministic() -> None:
    assert normalize_root_cause_key("Host Visual Evidence Floor") == "host-visual-evidence-floor"
    assert normalize_root_cause_key("host--visual__evidence floor") == "host-visual-evidence-floor"


def test_build_improvement_id_uses_skill_and_root_cause() -> None:
    assert (
        build_improvement_id(
            skill_id="cursor-meta-epic-executor",
            root_cause_key="Host Visual Evidence Floor",
        )
        == "improvement:cursor-meta-epic-executor:host-visual-evidence-floor"
    )


def test_derive_recurrence_from_valid_observation_count() -> None:
    assert derive_recurrence(0) == 0
    assert derive_recurrence(2) == 2
    with pytest.raises(ValueError, match=">="):
        derive_recurrence(-1)
    with pytest.raises(TypeError):
        derive_recurrence(True)  # type: ignore[arg-type]


def test_improvement_round_trip_and_canonical_json() -> None:
    plus_two = timezone(timedelta(hours=2))
    improvement = _base_improvement(
        first_seen=datetime(2026, 10, 30, 12, 0, tzinfo=plus_two),
        last_seen=datetime(2026, 10, 31, 11, 0, tzinfo=UTC),
        recurrence=2,
        repository_refs=["jannekbuengener/agent-workforce"],
        relations=[
            ImprovementRelation(
                related_improvement_id="improvement:other:similar-but-different",
                kind=DedupeRelationKind.RELATED,
                reason="similar symptoms, different root cause",
            )
        ],
        work_refs=[
            ImprovementWorkRef(
                schema_version=IMPROVEMENT_WORK_REF_SCHEMA,
                kind=WorkRefKind.GITHUB_ISSUE,
                repository_ref="jannekbuengener/agent-workforce",
                ref="44",
                url="https://github.com/jannekbuengener/agent-workforce/issues/44",
                linked_at=datetime(2026, 10, 31, 9, 0, tzinfo=UTC),
            )
        ],
        temporal=TemporalEnvelope(
            schema_version="temporal-envelope/v1",
            known_at=datetime(2026, 10, 30, 10, 0, tzinfo=UTC),
        ),
        resolution=ResolutionMeta(
            schema_version="resolution-meta/v1",
            confidence=0.75,
        ),
    )

    restored = Improvement.from_dict(improvement.to_dict())
    assert restored == improvement
    assert restored.first_seen == datetime(2026, 10, 30, 10, 0)
    serialized = serialize_contract(improvement.to_dict())
    json.loads(serialized)
    assert '"schema_version":"improvement/v1"' in serialized


def test_improvement_rejects_mismatched_identity() -> None:
    with pytest.raises(ValueError, match="improvement_id must equal"):
        _base_improvement(improvement_id="improvement:other:host-visual-evidence-floor")


def test_improvement_ignores_unknown_additive_v1_fields() -> None:
    restored = Improvement.from_dict(
        {
            **_base_improvement().to_dict(),
            "future_optional_field": {"enabled": True},
        }
    )
    assert "future_optional_field" not in restored.to_dict()


@pytest.mark.parametrize(
    ("current", "target", "allowed"),
    [
        (ImprovementLifecycle.NEW, ImprovementLifecycle.RECURRING, True),
        (ImprovementLifecycle.NEW, ImprovementLifecycle.VALIDATED, False),
        (ImprovementLifecycle.RECURRING, ImprovementLifecycle.VALIDATED, True),
        (ImprovementLifecycle.IMPLEMENTED, ImprovementLifecycle.VERIFIED, True),
        (ImprovementLifecycle.VERIFIED, ImprovementLifecycle.IMPLEMENTED, False),
        (ImprovementLifecycle.CLOSED, ImprovementLifecycle.NEW, False),
        (ImprovementLifecycle.VALIDATED, ImprovementLifecycle.VALIDATED, True),
    ],
)
def test_lifecycle_transition_matrix(
    current: ImprovementLifecycle,
    target: ImprovementLifecycle,
    allowed: bool,
) -> None:
    assert is_lifecycle_transition_allowed(current, target) is allowed
    if allowed:
        require_lifecycle_transition(current, target)
    else:
        with pytest.raises(ValueError, match="illegal lifecycle transition"):
            require_lifecycle_transition(current, target)


def test_closed_has_no_outbound_transitions() -> None:
    assert ALLOWED_LIFECYCLE_TRANSITIONS[ImprovementLifecycle.CLOSED] == frozenset()


def test_observation_round_trip_and_idempotency_key_required() -> None:
    observation = ImprovementObservation(
        schema_version=IMPROVEMENT_OBSERVATION_SCHEMA,
        observation_id="obs-1",
        agent_id="agent-a",
        run_id="run-1",
        skill_id="cursor-meta-epic-executor",
        observation="Visual capture happened mid-layout.",
        recommendation="Gate acceptance on stable geometry.",
        evidence=["pilot-run-log#12"],
        timestamp=datetime(2026, 10, 30, 10, 5, tzinfo=UTC),
        idempotency_key="run-1:obs-visual-floor",
        improvement_id="improvement:cursor-meta-epic-executor:host-visual-evidence-floor",
        root_cause_key="Host Visual Evidence Floor",
        confidence=0.7,
        provenance=Provenance(
            schema_version="provenance/v1",
            source_kind="skill-learning-recommendation",
            source_ref="agent-workforce#44",
        ),
    )

    restored = ImprovementObservation.from_dict(observation.to_dict())
    assert restored == observation
    assert restored.root_cause_key == "host-visual-evidence-floor"

    with pytest.raises(ValueError, match="idempotency_key"):
        ImprovementObservation(
            schema_version=IMPROVEMENT_OBSERVATION_SCHEMA,
            observation_id="obs-2",
            agent_id="agent-a",
            run_id="run-2",
            skill_id="cursor-meta-epic-executor",
            observation="x",
            recommendation="y",
            evidence=(),
            timestamp=datetime(2026, 10, 30, 10, 5, tzinfo=UTC),
            idempotency_key="  ",
        )


def test_merge_lineage_preserves_sources_and_rejects_self_merge() -> None:
    lineage = ImprovementMergeLineage(
        schema_version=IMPROVEMENT_MERGE_LINEAGE_SCHEMA,
        merge_id="merge-1",
        target_improvement_id="improvement:skill:a",
        source_improvement_ids=("improvement:skill:b",),
        actor_id="board-manager",
        reason="exact root_cause_key identity",
        evidence=["exact-identity"],
        merged_at=datetime(2026, 10, 31, 12, 0, tzinfo=UTC),
    )
    assert ImprovementMergeLineage.from_dict(lineage.to_dict()) == lineage

    with pytest.raises(ValueError, match="must not appear"):
        ImprovementMergeLineage(
            schema_version=IMPROVEMENT_MERGE_LINEAGE_SCHEMA,
            merge_id="merge-2",
            target_improvement_id="improvement:skill:a",
            source_improvement_ids=("improvement:skill:a",),
            actor_id="board-manager",
            reason="bad",
            evidence=(),
            merged_at=datetime(2026, 10, 31, 12, 0, tzinfo=UTC),
        )


def test_semantic_similarity_relation_is_not_exact_identity() -> None:
    relation = ImprovementRelation(
        related_improvement_id="improvement:skill:other",
        kind=DedupeRelationKind.POSSIBLE_DUPLICATE,
        reason="high textual similarity",
    )
    assert relation.kind is not DedupeRelationKind.EXACT_IDENTITY
    assert DedupeRelationKind.POSSIBLE_DUPLICATE.value == "POSSIBLE_DUPLICATE"


def test_improvement_rejects_incompatible_major() -> None:
    with pytest.raises(ValueError, match="major"):
        _base_improvement(schema_version="improvement/v2")
