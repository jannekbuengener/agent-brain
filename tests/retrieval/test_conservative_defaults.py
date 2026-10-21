"""Konservative Defaults-Tests (Slice 7, Task 6).

Stellen sicher, dass fehlende/ungültige Signale niemals einen
positiven Score erzeugen und der Retrieval-Core konservativ degradiert.
"""

from __future__ import annotations

import math

import pytest

from agent_brain.contracts import ArtifactRef, IndexRecord, RepositorySource
from agent_brain.core.policy import PolicyDecision, PolicyHook
from agent_brain.retrieval import (
    RetrievalPolicy,
    RetrievalQuery,
    SourcePriority,
    run_retrieval,
)


def _source() -> RepositorySource:
    return RepositorySource(
        schema_version="repository-source/v1",
        source_id="source-widgets",
        repository="example/widgets",
        revision="abc123",
        source_uri="https://example.invalid/widgets.git",
    )


def _artifact(artifact_id: str, source_hash: str, source_id: str = "source-widgets") -> ArtifactRef:
    return ArtifactRef(
        schema_version="artifact-ref/v1",
        artifact_id=artifact_id,
        source_id=source_id,
        source_path=f"src/{artifact_id}.py",
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


class DenyingHook(PolicyHook):
    def evaluate(self, context) -> PolicyDecision:
        return PolicyDecision(allowed=False, reasons=("policy_denied",))


def test_missing_lexical_signal_is_zero() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    record = _record("record-widget", artifact)

    result = run_retrieval(
        query=_query(),
        records=(record,),
        policy=_policy(),
        source_priority=None,
        lexical_signals={},
    )

    explanation = result.explanation[0]
    assert explanation.total_score == 0.0
    lexical_factor = next(
        f for f in explanation.factors if f.factor_name == "lexical"
    )
    assert lexical_factor.missing is True
    assert lexical_factor.normalized_value == 0.0


def test_unknown_source_priority_is_zero() -> None:
    artifact = _artifact("artifact-widget", "a" * 64, source_id="source-unknown")
    record = _record("record-widget", artifact)

    result = run_retrieval(
        query=_query(),
        records=(record,),
        policy=_policy(),
        source_priority=_source_priority(),
    )

    explanation = result.explanation[0]
    sp_factor = next(
        f for f in explanation.factors if f.factor_name == "source_priority"
    )
    assert sp_factor.normalized_value == 0.0


def test_semantic_always_conservative_zero() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    record = _record("record-widget", artifact)

    result = run_retrieval(
        query=_query(),
        records=(record,),
        policy=_policy(),
        source_priority=_source_priority(),
    )

    explanation = result.explanation[0]
    semantic_factor = next(
        f for f in explanation.factors if f.factor_name == "semantic"
    )
    assert semantic_factor.missing is True
    assert semantic_factor.normalized_value == 0.0


def test_evidence_provenance_always_conservative_zero() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    record = _record("record-widget", artifact)

    result = run_retrieval(
        query=_query(),
        records=(record,),
        policy=_policy(),
        source_priority=_source_priority(),
    )

    explanation = result.explanation[0]
    ep_factor = next(
        f for f in explanation.factors if f.factor_name == "evidence_provenance"
    )
    assert ep_factor.missing is True
    assert ep_factor.normalized_value == 0.0


def test_no_positive_score_from_missing_evidence() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    record = _record("record-widget", artifact)

    result = run_retrieval(
        query=_query(),
        records=(record,),
        policy=_policy(),
        source_priority=None,
        lexical_signals={"record-widget": 1.0},
    )

    # Auch mit maximalem lexical-Signal: kein positiver Beitrag aus
    # fehlenden Faktoren (semantic, graph, evidence_provenance = 0.0).
    assert result.explanation[0].total_score == pytest.approx(0.4)


def test_denying_stop_yields_no_positive_score() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    record = _record("record-widget", artifact)

    result = run_retrieval(
        query=_query(),
        records=(record,),
        policy=_policy(),
        source_priority=_source_priority(),
        stop_hook=DenyingHook(),
    )

    assert result.stop_applied is True
    assert result.candidates == ()
    assert result.total_score == 0.0


def test_duplicate_candidates_deduplicated() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    record = _record("record-dup", artifact)

    result = run_retrieval(
        query=_query(),
        records=(record, record),
        policy=_policy(),
        source_priority=_source_priority(),
    )

    assert len(result.candidates) == 1


def test_no_wall_clock_in_ranking() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    record = _record("record-widget", artifact)

    first = run_retrieval(
        query=_query(),
        records=(record,),
        policy=_policy(),
        source_priority=_source_priority(),
    )
    second = run_retrieval(
        query=_query(),
        records=(record,),
        policy=_policy(),
        source_priority=_source_priority(),
    )

    assert first == second


def test_nan_in_lexical_signal_is_zero() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    record = _record("record-widget", artifact)

    result = run_retrieval(
        query=_query(),
        records=(record,),
        policy=_policy(),
        source_priority=None,
        lexical_signals={"record-widget": float("nan")},
    )

    explanation = result.explanation[0]
    lexical_factor = next(
        f for f in explanation.factors if f.factor_name == "lexical"
    )
    assert not math.isnan(lexical_factor.normalized_value)
    assert explanation.total_score == 0.0
