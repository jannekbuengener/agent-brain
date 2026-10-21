"""Tie-breaking tests (Slice 7, Task 3).

RED-first: Diese Tests definieren den totalen, deterministischen
Tie-Break-Sortierschlüssel und müssen vor der Implementierung
fehlschlagen.
"""

from __future__ import annotations

from agent_brain.contracts import ArtifactRef, RepositorySource
from agent_brain.core.source_priority import SourcePriority
from agent_brain.retrieval.contract import (
    RankingFactor,
    RetrievalCandidate,
    RetrievalPolicy,
    RetrievalQuery,
)
from agent_brain.retrieval.ranking import rank_candidates

FIXTURE_SOURCE = RepositorySource(
    schema_version="repository-source/v1",
    source_id="source-widgets",
    repository="example/widgets",
    revision="abc123",
    source_uri="https://example.invalid/widgets.git",
)


def _artifact(artifact_id: str, source_id: str, source_hash: str) -> ArtifactRef:
    return ArtifactRef(
        schema_version="artifact-ref/v1",
        artifact_id=artifact_id,
        source_id=source_id,
        source_path=f"src/{artifact_id}.py",
        source_hash=source_hash,
        revision="abc123",
    )


def _candidate(
    record_id: str,
    artifact: ArtifactRef,
    score: float = 0.0,
    factors: tuple[RankingFactor, ...] = (),
) -> RetrievalCandidate:
    return RetrievalCandidate(
        schema_version="retrieval-candidate/v1",
        candidate_id=f"cand_{record_id}",
        record_id=record_id,
        artifact_ref=artifact,
        score=score,
        factors=factors,
    )


def _query() -> RetrievalQuery:
    return RetrievalQuery(
        schema_version="retrieval-query/v1",
        query_id="query-1",
        query_text="build widget",
        source_id="source-widgets",
    )


def _policy() -> RetrievalPolicy:
    return RetrievalPolicy(
        schema_version="retrieval-policy/v1",
        policy_id="policy-default",
        factor_weights={
            "lexical": 0.5,
            "semantic": 0.2,
            "graph": 0.2,
            "source_priority": 0.05,
            "evidence_provenance": 0.05,
        },
        default_factor_value=0.0,
        tie_break_keys=("record_id",),
        source_priority=("source-widgets", "source-other"),
    )


def _source_priority() -> SourcePriority:
    return SourcePriority(ordered_sources=("source-widgets", "source-other"))


def test_equal_scores_broken_by_record_id_ascending() -> None:
    artifact = _artifact("artifact-widget", "source-widgets", "a" * 64)
    candidates = (
        _candidate("record-zebra", artifact, score=0.5),
        _candidate("record-alpha", artifact, score=0.5),
        _candidate("record-mid", artifact, score=0.5),
    )
    policy = _policy()

    ranked = rank_candidates(
        candidates, policy=policy, source_priority=_source_priority()
    )

    assert [c.record_id for c, _ in ranked] == [
        "record-alpha",
        "record-mid",
        "record-zebra",
    ]


def test_different_scores_primary_sort_by_score_descending() -> None:
    artifact = _artifact("artifact-widget", "source-widgets", "a" * 64)
    candidates = (
        _candidate("record-low", artifact),
        _candidate("record-high", artifact),
        _candidate("record-mid", artifact),
    )
    policy = _policy()

    ranked = rank_candidates(
        candidates,
        policy=policy,
        source_priority=None,
        lexical_signals={
            "record-low": 0.1,
            "record-high": 0.9,
            "record-mid": 0.5,
        },
    )

    assert [c.record_id for c, _ in ranked] == [
        "record-high",
        "record-mid",
        "record-low",
    ]


def test_tie_break_total_order_deterministic() -> None:
    artifact = _artifact("artifact-widget", "source-widgets", "a" * 64)
    candidates = tuple(
        _candidate(f"record-{index:03d}", artifact, score=0.3) for index in range(10)
    )
    policy = _policy()

    ranked = rank_candidates(
        candidates, policy=policy, source_priority=_source_priority()
    )

    record_ids = [c.record_id for c, _ in ranked]
    assert record_ids == sorted(record_ids)
    # Running again must produce the same total order.
    again = rank_candidates(
        candidates, policy=policy, source_priority=_source_priority()
    )
    assert [c.record_id for c, _ in again] == record_ids


def test_input_reordering_does_not_change_tie_break_order() -> None:
    artifact = _artifact("artifact-widget", "source-widgets", "a" * 64)
    candidates = tuple(
        _candidate(f"record-{index:03d}", artifact, score=0.3) for index in range(10)
    )
    reversed_candidates = tuple(reversed(candidates))
    policy = _policy()

    first = rank_candidates(
        candidates, policy=policy, source_priority=_source_priority()
    )
    second = rank_candidates(
        reversed_candidates, policy=policy, source_priority=_source_priority()
    )

    assert [c.record_id for c, _ in first] == [c.record_id for c, _ in second]


def test_missing_factor_defaults_to_zero() -> None:
    artifact = _artifact("artifact-widget", "source-widgets", "a" * 64)
    candidates = (_candidate("record-widget", artifact, score=0.0),)
    policy = _policy()

    ranked = rank_candidates(
        candidates, policy=policy, source_priority=None
    )
    _, explanation = ranked[0]

    # All five factors should be present with 0.0 normalized value.
    factor_names = {f.factor_name for f in explanation.factors}
    expected = {"lexical", "semantic", "graph", "source_priority", "evidence_provenance"}
    assert factor_names == expected

    for factor in explanation.factors:
        assert factor.normalized_value == 0.0
        assert factor.missing is True
        assert factor.contribution == 0.0

    assert explanation.total_score == 0.0


def test_nan_and_infinity_treated_as_zero() -> None:
    import math

    artifact = _artifact("artifact-widget", "source-widgets", "a" * 64)
    candidate = _candidate("record-widget", artifact, score=0.0)
    policy = _policy()

    ranked = rank_candidates(
        (candidate,),
        policy=policy,
        source_priority=None,
        lexical_signals={"record-widget": float("nan")},
        graph_signals={"record-widget": float("inf")},
    )
    candidate, explanation = ranked[0]

    # NaN and Inf must not produce a positive score.
    assert explanation.total_score == 0.0
    for factor in explanation.factors:
        assert not math.isnan(factor.normalized_value)
        assert not math.isinf(factor.normalized_value)
        assert 0.0 <= factor.normalized_value <= 1.0


def test_no_dependency_on_dict_or_set_order() -> None:
    artifact = _artifact("artifact-widget", "source-widgets", "a" * 64)
    candidates = (
        _candidate("record-b", artifact, score=0.5),
        _candidate("record-a", artifact, score=0.5),
    )
    policy = _policy()

    ranked = rank_candidates(
        candidates, policy=policy, source_priority=_source_priority()
    )

    assert [c.record_id for c, _ in ranked] == ["record-a", "record-b"]


def test_candidate_without_claire_context_is_rankable() -> None:
    artifact = _artifact("artifact-widget", "source-widgets", "a" * 64)
    candidates = (_candidate("record-widget", artifact, score=0.0),)
    policy = _policy()

    ranked = rank_candidates(
        candidates, policy=policy, source_priority=_source_priority()
    )

    assert len(ranked) == 1
    assert ranked[0][0].record_id == "record-widget"


def test_no_host_paths_in_ranking() -> None:
    import agent_brain.retrieval.ranking as mod

    source = mod.__file__ or ""
    # No absolute host paths should be baked into ranking logic.
    assert "C:" not in source
    assert "/home/" not in source
    assert "/Users/" not in source
