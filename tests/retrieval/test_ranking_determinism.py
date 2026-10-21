"""Ranking determinism tests (Slice 7, Task 3).

RED-first: Diese Tests definieren das erwartete Verhalten des
deterministischen Hybrid-Rankers und müssen vor der Implementierung
fehlschlagen.
"""

from __future__ import annotations

import copy
from datetime import datetime

import pytest

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
            "lexical": 0.4,
            "semantic": 0.2,
            "graph": 0.2,
            "source_priority": 0.1,
            "evidence_provenance": 0.1,
        },
        default_factor_value=0.0,
        tie_break_keys=("record_id",),
        source_priority=("source-widgets", "source-other"),
    )


def _source_priority() -> SourcePriority:
    return SourcePriority(ordered_sources=("source-widgets", "source-other"))


def test_rank_identical_input_produces_identical_output() -> None:
    artifact = _artifact("artifact-widget", "source-widgets", "a" * 64)
    candidates = (
        _candidate("record-zebra", artifact),
        _candidate("record-alpha", artifact),
    )
    policy = _policy()

    first = rank_candidates(candidates, policy=policy, source_priority=_source_priority())
    second = rank_candidates(candidates, policy=policy, source_priority=_source_priority())

    assert first == second


def test_rank_input_reordering_produces_identical_output() -> None:
    artifact = _artifact("artifact-widget", "source-widgets", "a" * 64)
    candidates = tuple(
        _candidate(f"record-{index:03d}", artifact) for index in range(5)
    )
    reversed_candidates = tuple(reversed(candidates))
    policy = _policy()

    first = rank_candidates(candidates, policy=policy, source_priority=_source_priority())
    second = rank_candidates(
        reversed_candidates, policy=policy, source_priority=_source_priority()
    )

    assert [c.record_id for c, _ in first] == [c.record_id for c, _ in second]
    assert first == second


def test_rank_no_wall_clock_dependency() -> None:
    artifact = _artifact("artifact-widget", "source-widgets", "a" * 64)
    candidates = (_candidate("record-widget", artifact),)
    policy = _policy()

    datetime.now()
    result = rank_candidates(
        candidates, policy=policy, source_priority=_source_priority()
    )

    again = rank_candidates(
        candidates, policy=policy, source_priority=_source_priority()
    )
    assert result == again


def test_rank_semantic_missing_is_conservative_zero() -> None:
    artifact = _artifact("artifact-widget", "source-widgets", "a" * 64)
    candidates = (_candidate("record-widget", artifact),)
    policy = _policy()

    ranked = rank_candidates(
        candidates, policy=policy, source_priority=_source_priority()
    )
    _, explanation = ranked[0]

    semantic_factor = next(
        (f for f in explanation.factors if f.factor_name == "semantic"), None
    )
    assert semantic_factor is not None
    assert semantic_factor.normalized_value == 0.0
    assert semantic_factor.missing is True
    assert semantic_factor.contribution == 0.0


def test_rank_graph_missing_is_conservative_zero() -> None:
    artifact = _artifact("artifact-widget", "source-widgets", "a" * 64)
    candidates = (_candidate("record-widget", artifact),)
    policy = _policy()

    ranked = rank_candidates(
        candidates, policy=policy, source_priority=_source_priority()
    )
    _, explanation = ranked[0]

    graph_factor = next(
        (f for f in explanation.factors if f.factor_name == "graph"), None
    )
    assert graph_factor is not None
    assert graph_factor.normalized_value == 0.0
    assert graph_factor.missing is True


def test_rank_source_priority_unknown_is_zero() -> None:
    artifact = _artifact("artifact-widget", "source-unknown", "a" * 64)
    candidates = (_candidate("record-widget", artifact),)
    policy = _policy()

    ranked = rank_candidates(
        candidates, policy=policy, source_priority=_source_priority()
    )
    _, explanation = ranked[0]

    sp_factor = next(
        (f for f in explanation.factors if f.factor_name == "source_priority"), None
    )
    assert sp_factor is not None
    assert sp_factor.normalized_value == 0.0


def test_rank_evidence_provenance_missing_is_zero() -> None:
    artifact = _artifact("artifact-widget", "source-widgets", "a" * 64)
    candidates = (_candidate("record-widget", artifact),)
    policy = _policy()

    ranked = rank_candidates(
        candidates, policy=policy, source_priority=_source_priority()
    )
    _, explanation = ranked[0]

    ep_factor = next(
        (f for f in explanation.factors if f.factor_name == "evidence_provenance"),
        None,
    )
    assert ep_factor is not None
    assert ep_factor.normalized_value == 0.0
    assert ep_factor.missing is True


def test_rank_total_score_is_weighted_sum() -> None:
    artifact = _artifact("artifact-widget", "source-widgets", "a" * 64)
    candidate = _candidate("record-widget", artifact, score=0.0)
    policy = _policy()

    ranked = rank_candidates(
        (candidate,),
        policy=policy,
        source_priority=None,
        lexical_signals={"record-widget": 0.5},
    )
    candidate, explanation = ranked[0]

    assert explanation.total_score == pytest.approx(0.2)
    assert candidate.score == pytest.approx(0.2)


def test_rank_explanation_is_deterministic() -> None:
    artifact = _artifact("artifact-widget", "source-widgets", "a" * 64)
    candidates = (_candidate("record-widget", artifact),)
    policy = _policy()

    first = rank_candidates(
        candidates, policy=policy, source_priority=_source_priority()
    )
    second = rank_candidates(
        candidates, policy=policy, source_priority=_source_priority()
    )

    assert first == second
    assert copy.deepcopy(first) == copy.deepcopy(second)


def test_rank_unknown_factor_has_no_positive_effect() -> None:
    artifact = _artifact("artifact-widget", "source-widgets", "a" * 64)
    candidates = (_candidate("record-widget", artifact),)
    policy = _policy()

    # Unknown factor should not appear in explanation or affect score.
    ranked = rank_candidates(
        candidates, policy=policy, source_priority=_source_priority()
    )
    _, explanation = ranked[0]

    factor_names = {f.factor_name for f in explanation.factors}
    assert "unknown_factor" not in factor_names
    assert explanation.total_score >= 0.0


def test_rank_no_claire_or_trading_terms() -> None:
    import agent_brain.retrieval.ranking as mod

    source = mod.__file__ or ""
    assert "claire" not in source.lower()
    assert "trading" not in source.lower()
    assert "surrealdb" not in source.lower()


def test_explanation_source_refs_contain_no_host_paths() -> None:
    artifact = ArtifactRef(
        schema_version="artifact-ref/v1",
        artifact_id="artifact-widget",
        source_id="source-widgets",
        source_path="C:/absolute/host/path/widget.py",
        source_hash="a" * 64,
        revision="abc123",
    )
    candidate = _candidate("record-widget", artifact, score=0.0)
    policy = _policy()

    ranked = rank_candidates(
        (candidate,), policy=policy, source_priority=None
    )
    candidate, explanation = ranked[0]

    for ref in explanation.source_refs:
        assert ":" not in ref
        assert not ref.startswith("/")
        assert not ref.startswith("\\")
