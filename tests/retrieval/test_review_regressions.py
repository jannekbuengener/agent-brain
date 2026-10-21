"""Regression tests for blocking PR #35 review findings."""

from __future__ import annotations

from agent_brain.context.required_reads import RequiredRead
from agent_brain.contracts import ArtifactRef, GraphEdge, IndexRecord
from agent_brain.core.policy import PolicyDecision, PolicyHook
from agent_brain.retrieval import (
    RetrievalPolicy,
    RetrievalQuery,
    annotate_impact,
    collect_candidates,
    run_retrieval,
)
from agent_brain.retrieval.contract import RetrievalCandidate
from agent_brain.retrieval.required_reads import RetrievalRequiredReadsResult


def _artifact() -> ArtifactRef:
    return ArtifactRef(
        schema_version="artifact-ref/v1",
        artifact_id="artifact-widget",
        source_id="source-widgets",
        source_path="src/widget.py",
        source_hash="a" * 64,
        revision="abc123",
    )


def _record(record_id: str, record_type: str = "symbol") -> IndexRecord:
    return IndexRecord(
        schema_version="index-record/v1",
        record_id=record_id,
        record_type=record_type,
        source=_artifact(),
        content_hash="b" * 64,
        attributes={},
    )


def _query(*, limit: int = 10, record_types: tuple[str, ...] = (), required_reads: tuple[str, ...] = ()) -> RetrievalQuery:
    return RetrievalQuery(
        schema_version="retrieval-query/v1",
        query_id="query-review",
        query_text="widget",
        source_id="source-widgets",
        record_type_filter=record_types,
        limit=limit,
        required_reads=required_reads,
    )


def _policy(**weights: float) -> RetrievalPolicy:
    factor_weights = weights or {
        "lexical": 0.4,
        "semantic": 0.2,
        "graph": 0.2,
        "source_priority": 0.1,
        "evidence_provenance": 0.1,
    }
    return RetrievalPolicy(
        schema_version="retrieval-policy/v1",
        policy_id="review-policy",
        factor_weights=factor_weights,
        default_factor_value=0.0,
        tie_break_keys=("record_id",),
    )


def test_out_of_range_signal_is_conservative_zero() -> None:
    result = run_retrieval(
        query=_query(),
        records=(_record("record-a"),),
        policy=_policy(),
        lexical_signals={"record-a": 2.0},
    )
    lexical = next(
        factor
        for factor in result.explanation[0].factors
        if factor.factor_name == "lexical"
    )
    assert lexical.normalized_value == 0.0
    assert lexical.contribution == 0.0


def test_candidate_collection_applies_record_type_filter() -> None:
    candidates = collect_candidates(
        (_record("record-module", "module"), _record("record-symbol", "symbol")),
        query=_query(record_types=("symbol",)),
    )
    assert [candidate.record_id for candidate in candidates] == ["record-symbol"]


def test_run_retrieval_enforces_query_limit_after_ranking() -> None:
    records = tuple(_record(f"record-{index}") for index in range(3))
    result = run_retrieval(
        query=_query(limit=1),
        records=records,
        policy=_policy(),
        lexical_signals={
            "record-0": 0.1,
            "record-1": 0.9,
            "record-2": 0.5,
        },
    )
    assert [candidate.record_id for candidate in result.candidates] == ["record-1"]


def test_run_retrieval_derives_graph_signals_from_edges() -> None:
    records = (_record("record-a"), _record("record-b"))
    edges = (
        GraphEdge(
            schema_version="graph-edge/v1",
            edge_id="edge-a-b",
            from_id="record-a",
            to_id="record-b",
            edge_type="contains",
            confidence=1.0,
            inferred=False,
        ),
    )
    result = run_retrieval(
        query=_query(),
        records=records,
        edges=edges,
        policy=_policy(graph=1.0),
    )
    assert all(candidate.score > 0.0 for candidate in result.candidates)


def test_impact_nan_signal_degrades_to_zero() -> None:
    candidate = RetrievalCandidate(
        schema_version="retrieval-candidate/v1",
        candidate_id="cand_record-a",
        record_id="record-a",
        artifact_ref=_artifact(),
        score=0.0,
        factors=(),
    )
    impacts = annotate_impact(
        (candidate,),
        graph_signals={"record-a": float("nan")},
        policy=_policy(),
    )
    assert impacts[0].signal_value == 0.0


class _RequiredReadAwareHook(PolicyHook):
    def evaluate(self, context) -> PolicyDecision:
        available = context.attributes.get("required_reads_available")
        return PolicyDecision(
            allowed=available is True,
            reasons=() if available is True else ("required_reads_unavailable",),
        )


def test_run_retrieval_exposes_required_read_state_to_policy() -> None:
    required_read_result = RetrievalRequiredReadsResult(
        required_reads=(
            RequiredRead(
                path="AGENTS.md",
                priority="critical",
                reason="repository baseline",
                available=False,
                warning="not_available",
            ),
        ),
        limitations=("required_reads_not_all_available",),
    )
    result = run_retrieval(
        query=_query(required_reads=("AGENTS.md",)),
        records=(_record("record-a"),),
        policy=_policy(),
        stop_hook=_RequiredReadAwareHook(),
        required_reads_result=required_read_result,
    )
    assert result.stop_applied is True
    assert result.candidates == ()
    assert "required_reads_not_all_available" in result.limitations


def test_run_retrieval_preserves_impact_annotations() -> None:
    records = (_record("record-a"), _record("record-b"))
    edges = (
        GraphEdge(
            schema_version="graph-edge/v1",
            edge_id="edge-a-b",
            from_id="record-a",
            to_id="record-b",
            edge_type="contains",
            confidence=1.0,
            inferred=False,
        ),
    )
    result = run_retrieval(
        query=_query(),
        records=records,
        edges=edges,
        policy=_policy(graph=1.0),
    )
    assert result.impact_applied is True
    assert len(result.impacts) == 2
    assert {impact.candidate_id for impact in result.impacts} == {
        "cand_record-a",
        "cand_record-b",
    }


class _AllowingHook(PolicyHook):
    def evaluate(self, context) -> PolicyDecision:
        return PolicyDecision(allowed=True, reasons=())


def test_allowed_policy_does_not_mark_stop_applied() -> None:
    result = run_retrieval(
        query=_query(),
        records=(_record("record-a"),),
        policy=_policy(),
        stop_hook=_AllowingHook(),
    )
    assert result.stop_applied is False
    assert result.candidates
