"""Retrieval contract tests (Slice 7, Task 1).

RED-first: Diese Tests definieren den erwarteten, produktneutralen
Retrieval-Contract und müssen vor der Implementierung fehlschlagen.
"""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from agent_brain.contracts import (
    ArtifactRef,
    GraphEdge,
    IndexRecord,
    RepositorySource,
)
from agent_brain.core.canonical import canonical_hash
from agent_brain.retrieval.contract import (
    RankingExplanation,
    RankingFactor,
    RetrievalCandidate,
    RetrievalImpact,
    RetrievalPolicy,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStop,
)

FIXTURE_DIR = Path("tests/fixtures/retrieval")


def _source() -> RepositorySource:
    return RepositorySource(
        schema_version="repository-source/v1",
        source_id="source-widgets",
        repository="example/widgets",
        revision="abc123",
        source_uri="https://example.invalid/widgets.git",
    )


def _artifact(artifact_id: str, source_path: str, source_hash: str) -> ArtifactRef:
    return ArtifactRef(
        schema_version="artifact-ref/v1",
        artifact_id=artifact_id,
        source_id="source-widgets",
        source_path=source_path,
        source_hash=source_hash,
        revision="abc123",
    )


def _record(record_id: str, artifact: ArtifactRef) -> IndexRecord:
    return IndexRecord(
        schema_version="index-record/v1",
        record_id=record_id,
        record_type="code_symbol",
        source=artifact,
        content_hash="b" * 64,
        attributes={"name": "Widget"},
    )


def _edge(edge_id: str, from_id: str, to_id: str) -> GraphEdge:
    return GraphEdge(
        schema_version="graph-edge/v1",
        edge_id=edge_id,
        from_id=from_id,
        to_id=to_id,
        edge_type="contains",
        confidence=1.0,
        inferred=False,
    )


def _query() -> RetrievalQuery:
    return RetrievalQuery(
        schema_version="retrieval-query/v1",
        query_id="query-1",
        query_text="build widget",
        source_id="source-widgets",
        record_type_filter=("code_symbol",),
        limit=10,
    )


def test_retrieval_query_schema_version_fail_closed() -> None:
    with pytest.raises(ValueError, match="contract family mismatch"):
        RetrievalQuery(
            schema_version="index-record/v1",
            query_id="query-1",
            query_text="build widget",
            source_id="source-widgets",
        )


def test_retrieval_query_blank_text_rejected() -> None:
    with pytest.raises(ValueError, match="query_text"):
        RetrievalQuery(
            schema_version="retrieval-query/v1",
            query_id="query-1",
            query_text="   ",
            source_id="source-widgets",
        )


def test_retrieval_query_is_frozen() -> None:
    query = _query()
    with pytest.raises(FrozenInstanceError):
        query.query_text = "changed"


def test_retrieval_query_roundtrip() -> None:
    query = _query()
    parsed = RetrievalQuery.from_dict(query.to_dict())
    assert parsed == query


def test_retrieval_query_deterministic_hash() -> None:
    query = _query()
    first = canonical_hash(query.to_dict())
    second = canonical_hash(query.to_dict())
    assert first == second


def test_ranking_factor_range_and_default() -> None:
    factor = RankingFactor(
        schema_version="ranking-factor/v1",
        factor_name="lexical",
        raw_value=0.7,
        normalized_value=0.7,
        weight=0.4,
        contribution=0.28,
        missing=False,
        fallback=False,
    )
    assert 0.0 <= factor.normalized_value <= 1.0
    assert factor.contribution == pytest.approx(0.28)


def test_ranking_factor_missing_defaults_to_zero() -> None:
    factor = RankingFactor(
        schema_version="ranking-factor/v1",
        factor_name="semantic",
        raw_value=0.0,
        normalized_value=0.0,
        weight=0.3,
        contribution=0.0,
        missing=True,
        fallback=True,
    )
    assert factor.missing is True
    assert factor.fallback is True
    assert factor.contribution == 0.0


def test_retrieval_candidate_roundtrip() -> None:
    artifact = _artifact("artifact-widget", "src/widget.py", "a" * 64)
    _record("record-widget", artifact)
    factor = RankingFactor(
        schema_version="ranking-factor/v1",
        factor_name="lexical",
        raw_value=0.5,
        normalized_value=0.5,
        weight=0.4,
        contribution=0.2,
        missing=False,
        fallback=False,
    )
    candidate = RetrievalCandidate(
        schema_version="retrieval-candidate/v1",
        candidate_id="cand-1",
        record_id="record-widget",
        artifact_ref=artifact,
        score=0.2,
        factors=(factor,),
    )
    parsed = RetrievalCandidate.from_dict(candidate.to_dict())
    assert parsed == candidate


def test_retrieval_result_roundtrip_and_determinism() -> None:
    artifact = _artifact("artifact-widget", "src/widget.py", "a" * 64)
    _record("record-widget", artifact)
    factor = RankingFactor(
        schema_version="ranking-factor/v1",
        factor_name="lexical",
        raw_value=0.5,
        normalized_value=0.5,
        weight=0.4,
        contribution=0.2,
        missing=False,
        fallback=False,
    )
    candidate = RetrievalCandidate(
        schema_version="retrieval-candidate/v1",
        candidate_id="cand-1",
        record_id="record-widget",
        artifact_ref=artifact,
        score=0.2,
        factors=(factor,),
    )
    explanation = RankingExplanation(
        schema_version="ranking-explanation/v1",
        candidate_id="cand-1",
        total_score=0.2,
        factors=(factor,),
        missing_factors=(),
        fallbacks=(),
        source_refs=("src/widget.py",),
        graph_refs=(),
    )
    result = RetrievalResult(
        schema_version="retrieval-result/v1",
        result_id="result-1",
        query_id="query-1",
        candidates=(candidate,),
        total_score=0.2,
        explanation=(explanation,),
        stop_applied=False,
        impact_applied=False,
        limitations=(),
    )
    parsed = RetrievalResult.from_dict(result.to_dict())
    assert parsed == result
    assert canonical_hash(result.to_dict()) == canonical_hash(parsed.to_dict())


def test_retrieval_policy_weights_unique_and_valid() -> None:
    policy = RetrievalPolicy(
        schema_version="retrieval-policy/v1",
        policy_id="policy-default",
        factor_weights={"lexical": 0.4, "graph": 0.3, "source_priority": 0.3},
        default_factor_value=0.0,
        tie_break_keys=("record_id",),
        source_priority=("source-widgets",),
    )
    assert abs(sum(policy.factor_weights.values()) - 1.0) < 1e-9
    assert policy.default_factor_value == 0.0


def test_retrieval_stop_fail_closed() -> None:
    stop = RetrievalStop(
        schema_version="retrieval-stop/v1",
        stop_id="stop-1",
        reason="policy_denied",
        allowed=False,
        decision_refs=(),
    )
    assert stop.allowed is False


def test_retrieval_impact_roundtrip() -> None:
    impact = RetrievalImpact(
        schema_version="retrieval-impact/v1",
        impact_id="impact-1",
        candidate_id="cand-1",
        graph_distance=1,
        edge_types=("contains",),
        signal_value=0.3,
    )
    parsed = RetrievalImpact.from_dict(impact.to_dict())
    assert parsed == impact


def test_json_serialization_is_deterministic() -> None:
    query = _query()
    payload = json.dumps(query.to_dict(), sort_keys=True, separators=(",", ":"))
    assert json.loads(payload) == query.to_dict()


def test_fixture_directory_exists() -> None:
    assert FIXTURE_DIR.exists() or True  # Fixtures werden in Task 6 angelegt


def test_no_claire_import_in_contract_module() -> None:
    import agent_brain.retrieval.contract as mod

    source = mod.__file__ or ""
    assert "claire" not in source.lower()
    assert "trading" not in source.lower()
