"""Deterministic candidate collection tests (Slice 7, Task 2).

RED-first: Diese Tests definieren das erwartete Verhalten der
Retrieval-Kandidaten-Sammlung und müssen vor der Implementierung
fehlschlagen.
"""

from __future__ import annotations

from agent_brain.contracts import ArtifactRef, GraphEdge, IndexRecord, RepositorySource
from agent_brain.retrieval.contract import RetrievalQuery
from agent_brain.retrieval.retriever import collect_candidates

FIXTURE_SOURCE = RepositorySource(
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
    )


def test_empty_records_yield_empty_candidates() -> None:
    result = collect_candidates((), edges=(), query=_query())
    assert result == ()


def test_single_record_yields_single_candidate() -> None:
    artifact = _artifact("artifact-widget", "src/widget.py", "a" * 64)
    record = _record("record-widget", artifact)
    result = collect_candidates((record,), edges=(), query=_query())
    assert len(result) == 1
    candidate = result[0]
    assert candidate.record_id == "record-widget"
    assert candidate.artifact_ref == artifact
    assert candidate.score == 0.0
    assert candidate.factors == ()


def test_candidates_sorted_by_record_id_independent_of_input_order() -> None:
    artifact = _artifact("artifact-widget", "src/widget.py", "a" * 64)
    first = _record("record-zebra", artifact)
    second = _record("record-alpha", artifact)
    third = _record("record-mid", artifact)

    shuffled = (third, first, second)
    result = collect_candidates(shuffled, edges=(), query=_query())

    assert [c.record_id for c in result] == [
        "record-alpha",
        "record-mid",
        "record-zebra",
    ]


def test_duplicate_records_deduplicated_by_record_id() -> None:
    artifact = _artifact("artifact-widget", "src/widget.py", "a" * 64)
    record = _record("record-dup", artifact)
    result = collect_candidates((record, record), edges=(), query=_query())
    assert len(result) == 1
    assert result[0].record_id == "record-dup"


def test_same_artifact_multiple_records_kept_separately() -> None:
    artifact = _artifact("artifact-widget", "src/widget.py", "a" * 64)
    first = _record("record-one", artifact)
    second = _record("record-two", artifact)
    result = collect_candidates((second, first), edges=(), query=_query())
    assert len(result) == 2
    assert [c.record_id for c in result] == ["record-one", "record-two"]


def test_graph_edges_accepted_without_crash() -> None:
    artifact = _artifact("artifact-widget", "src/widget.py", "a" * 64)
    record = _record("record-widget", artifact)
    edge = _edge("edge-1", "record-widget", "record-widget")
    result = collect_candidates((record,), edges=(edge,), query=_query())
    assert len(result) == 1
    assert result[0].record_id == "record-widget"


def test_unknown_graph_edges_do_not_affect_candidates() -> None:
    artifact = _artifact("artifact-widget", "src/widget.py", "a" * 64)
    record = _record("record-widget", artifact)
    dangling = _edge("edge-dangling", "record-missing", "record-also-missing")
    result = collect_candidates((record,), edges=(dangling,), query=_query())
    assert len(result) == 1
    assert result[0].record_id == "record-widget"


def test_input_reordering_produces_identical_output() -> None:
    artifact = _artifact("artifact-widget", "src/widget.py", "a" * 64)
    records = tuple(
        _record(f"record-{index:03d}", artifact) for index in range(5)
    )
    reversed_records = tuple(reversed(records))

    first = collect_candidates(records, edges=(), query=_query())
    second = collect_candidates(reversed_records, edges=(), query=_query())

    assert [c.record_id for c in first] == [c.record_id for c in second]
    assert first == second


def test_candidates_have_deterministic_candidate_ids() -> None:
    artifact = _artifact("artifact-widget", "src/widget.py", "a" * 64)
    record = _record("record-stable", artifact)
    result = collect_candidates((record,), edges=(), query=_query())
    assert result[0].candidate_id == "cand_record-stable"


def test_no_wall_clock_in_candidate_collection() -> None:
    artifact = _artifact("artifact-widget", "src/widget.py", "a" * 64)
    record = _record("record-widget", artifact)
    result = collect_candidates((record,), edges=(), query=_query())
    candidate = result[0]
    assert candidate.score == 0.0
    assert candidate.factors == ()


def test_unsupported_record_type_still_collected() -> None:
    artifact = _artifact("artifact-widget", "src/widget.py", "a" * 64)
    record = IndexRecord(
        schema_version="index-record/v1",
        record_id="record-unknown",
        record_type="unsupported_type",
        source=artifact,
        content_hash=None,
        attributes={},
    )
    result = collect_candidates((record,), edges=(), query=_query())
    assert len(result) == 1
    assert result[0].record_id == "record-unknown"
