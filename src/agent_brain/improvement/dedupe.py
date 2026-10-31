"""Conservative Improvement dedupe / merge helpers (#49).

Exact identity may attach observations. Semantic similarity alone never
auto-merges — it yields candidate relations for Board Manager review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime

from agent_brain.contracts.improvement import (
    IMPROVEMENT_MERGE_LINEAGE_SCHEMA,
    DedupeRelationKind,
    Improvement,
    ImprovementMergeLineage,
    ImprovementObservation,
    ImprovementRelation,
    build_improvement_id,
    normalize_root_cause_key,
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True, slots=True)
class DedupeSignal:
    """Explainable, non-opaque dedupe signal."""

    name: str
    detail: str


@dataclass(frozen=True, slots=True)
class DedupeAssessment:
    """Result of comparing a new observation/root cause to existing records."""

    kind: DedupeRelationKind | str
    target_improvement_id: str | None
    signals: tuple[DedupeSignal, ...]
    auto_merge_allowed: bool

    def __post_init__(self) -> None:
        if self.kind == DedupeRelationKind.EXACT_IDENTITY and not self.auto_merge_allowed:
            raise ValueError("EXACT_IDENTITY assessments must allow auto attach/merge")
        if self.kind != DedupeRelationKind.EXACT_IDENTITY and self.auto_merge_allowed:
            raise ValueError("only EXACT_IDENTITY may set auto_merge_allowed=True")


def _tokens(text: str) -> frozenset[str]:
    return frozenset(_TOKEN_RE.findall(text.lower()))


def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def assess_observation(
    observation: ImprovementObservation,
    candidates: tuple[Improvement, ...] | list[Improvement],
    *,
    strong_similarity_threshold: float = 0.72,
    weak_similarity_threshold: float = 0.40,
) -> DedupeAssessment:
    """Classify an observation against existing Improvements.

    Conservative rules:
    1. Exact ``root_cause_key`` (+ skill scope) → EXACT_IDENTITY (auto attach OK)
    2. High textual similarity + same skill → POSSIBLE_DUPLICATE (no auto-merge)
    3. Weak similarity → RELATED (no auto-merge)
    4. Otherwise → NEW
    """
    if observation.root_cause_key is not None:
        key = normalize_root_cause_key(observation.root_cause_key)
        expected_id = build_improvement_id(
            skill_id=observation.skill_id,
            root_cause_key=key,
        )
        for candidate in candidates:
            if candidate.skill_id != observation.skill_id:
                continue
            if candidate.root_cause_key == key or candidate.improvement_id == expected_id:
                return DedupeAssessment(
                    kind=DedupeRelationKind.EXACT_IDENTITY,
                    target_improvement_id=candidate.improvement_id,
                    signals=(
                        DedupeSignal(
                            name="exact_root_cause_key",
                            detail=f"root_cause_key={key}",
                        ),
                    ),
                    auto_merge_allowed=True,
                )
            if expected_id in candidate.aliases:
                return DedupeAssessment(
                    kind=DedupeRelationKind.EXACT_IDENTITY,
                    target_improvement_id=candidate.improvement_id,
                    signals=(
                        DedupeSignal(
                            name="alias_identity",
                            detail=f"alias={expected_id}",
                        ),
                    ),
                    auto_merge_allowed=True,
                )

    # Similarity scoring intentionally ignores root_cause_key tokens: differing
    # keys already failed exact identity, and including them would hide strong
    # symptom/recommendation overlap that still must not auto-merge.
    obs_tokens = _tokens(f"{observation.observation} {observation.recommendation}")
    best: tuple[float, Improvement, str] | None = None
    for candidate in candidates:
        if candidate.skill_id != observation.skill_id:
            continue
        score = _jaccard(
            obs_tokens,
            _tokens(f"{candidate.summary} {candidate.recommendation}"),
        )
        if best is None or score > best[0]:
            best = (score, candidate, "token_jaccard")

    if best is None:
        return DedupeAssessment(
            kind="NEW",
            target_improvement_id=None,
            signals=(DedupeSignal(name="no_candidates", detail="empty candidate set"),),
            auto_merge_allowed=False,
        )

    score, candidate, signal_name = best
    if score >= strong_similarity_threshold:
        return DedupeAssessment(
            kind=DedupeRelationKind.POSSIBLE_DUPLICATE,
            target_improvement_id=candidate.improvement_id,
            signals=(
                DedupeSignal(
                    name=signal_name,
                    detail=f"score={score:.3f} threshold={strong_similarity_threshold:.3f}",
                ),
                DedupeSignal(
                    name="auto_merge_blocked",
                    detail="semantic similarity alone must not auto-merge",
                ),
            ),
            auto_merge_allowed=False,
        )
    if score >= weak_similarity_threshold:
        return DedupeAssessment(
            kind=DedupeRelationKind.RELATED,
            target_improvement_id=candidate.improvement_id,
            signals=(
                DedupeSignal(
                    name=signal_name,
                    detail=f"score={score:.3f} threshold={weak_similarity_threshold:.3f}",
                ),
            ),
            auto_merge_allowed=False,
        )
    return DedupeAssessment(
        kind="NEW",
        target_improvement_id=None,
        signals=(
            DedupeSignal(
                name=signal_name,
                detail=f"score={score:.3f} below weak threshold",
            ),
        ),
        auto_merge_allowed=False,
    )


def relate_improvements(
    left: Improvement,
    right: Improvement,
    *,
    kind: DedupeRelationKind,
    reason: str,
) -> tuple[Improvement, Improvement]:
    """Attach symmetric conservative relations without merging identities."""
    if kind is DedupeRelationKind.EXACT_IDENTITY:
        raise ValueError("use merge_improvements for EXACT_IDENTITY consolidation")
    left_rel = ImprovementRelation(
        related_improvement_id=right.improvement_id,
        kind=kind,
        reason=reason,
    )
    right_rel = ImprovementRelation(
        related_improvement_id=left.improvement_id,
        kind=kind,
        reason=reason,
    )
    return (
        replace(left, relations=(*left.relations, left_rel), revision=left.revision + 1),
        replace(right, relations=(*right.relations, right_rel), revision=right.revision + 1),
    )


def merge_improvements(
    *,
    target: Improvement,
    sources: tuple[Improvement, ...] | list[Improvement],
    actor_id: str,
    reason: str,
    evidence: tuple[str, ...] | list[str],
    merged_at: datetime,
    merge_id: str,
) -> tuple[Improvement, tuple[Improvement, ...], ImprovementMergeLineage]:
    """Merge source Improvements into target with full lineage.

    Sources become superseded aliases. Callers (Management Port) must authorize
    this mutation — observation writers must not invoke it blindly on similarity.
    """
    source_list = tuple(sources)
    if not source_list:
        raise ValueError("sources must not be empty")
    source_ids = tuple(item.improvement_id for item in source_list)
    if target.improvement_id in source_ids:
        raise ValueError("target must not be listed as a source")
    for source in source_list:
        if source.skill_id != target.skill_id:
            raise ValueError("refusing cross-skill merge without explicit management override")

    lineage = ImprovementMergeLineage(
        schema_version=IMPROVEMENT_MERGE_LINEAGE_SCHEMA,
        merge_id=merge_id,
        target_improvement_id=target.improvement_id,
        source_improvement_ids=source_ids,
        actor_id=actor_id,
        reason=reason,
        evidence=tuple(evidence),
        merged_at=merged_at,
    )

    aliases = tuple(
        dict.fromkeys(
            [
                *target.aliases,
                *[source.improvement_id for source in source_list],
                *[alias for source in source_list for alias in source.aliases],
            ]
        )
    )
    repository_refs = tuple(
        dict.fromkeys(
            [
                *target.repository_refs,
                *[ref for source in source_list for ref in source.repository_refs],
            ]
        )
    )
    first_seen = min([target.first_seen, *[source.first_seen for source in source_list]])
    last_seen = max([target.last_seen, *[source.last_seen for source in source_list]])
    # recurrence stays derived from observation history; caller/store must refresh
    # after relocating observation events. Do not invent a client-side ++ here.

    merged_target = replace(
        target,
        aliases=aliases,
        repository_refs=repository_refs,
        first_seen=first_seen,
        last_seen=last_seen,
        merge_lineage=(*target.merge_lineage, lineage),
        revision=target.revision + 1,
    )
    superseded = tuple(
        replace(
            source,
            superseded_by_improvement_id=target.improvement_id,
            revision=source.revision + 1,
        )
        for source in source_list
    )
    return merged_target, superseded, lineage
