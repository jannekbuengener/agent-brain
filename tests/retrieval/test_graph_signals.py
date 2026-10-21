"""Graph signal tests (Slice 7, Task 4).

RED-first: Diese Tests definieren das erwartete Verhalten der
produktneutralen Graph-/Struktur-Signale aus bestehenden GraphEdge-
Contracts und müssen vor der Implementierung fehlschlagen.
"""

from __future__ import annotations

import pytest

from agent_brain.contracts import ArtifactRef, GraphEdge, IndexRecord
from agent_brain.retrieval.graph_signals import compute_graph_signals


def _artifact(artifact_id: str, source_hash: str) -> ArtifactRef:
    return ArtifactRef(
        schema_version="artifact-ref/v1",
        artifact_id=artifact_id,
        source_id="source-widgets",
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


def _edge(
    edge_id: str,
    from_id: str,
    to_id: str,
    edge_type: str = "contains",
    confidence: float = 1.0,
    inferred: bool = False,
) -> GraphEdge:
    return GraphEdge(
        schema_version="graph-edge/v1",
        edge_id=edge_id,
        from_id=from_id,
        to_id=to_id,
        edge_type=edge_type,
        confidence=confidence,
        inferred=inferred,
    )


def test_empty_graph_yields_zero_signal() -> None:
    result = compute_graph_signals((), edges=())
    assert result == {}


def test_single_edge_produces_signal_for_involved_records() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    record_a = _record("record-a", artifact)
    record_b = _record("record-b", artifact)
    edge = _edge("edge-1", "record-a", "record-b")

    result = compute_graph_signals((record_a, record_b), edges=(edge,))

    assert "record-a" in result
    assert "record-b" in result
    assert 0.0 <= result["record-a"] <= 1.0
    assert 0.0 <= result["record-b"] <= 1.0


def test_input_reordering_produces_identical_signals() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    records = tuple(
        _record(f"record-{index}", artifact) for index in range(5)
    )
    edges = tuple(
        _edge(f"edge-{index}", f"record-{index}", f"record-{(index + 1) % 5}")
        for index in range(5)
    )

    first = compute_graph_signals(records, edges=edges)
    second = compute_graph_signals(tuple(reversed(records)), edges=tuple(reversed(edges)))

    assert first == second


def test_duplicate_edges_do_not_double_signal() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    record_a = _record("record-a", artifact)
    record_b = _record("record-b", artifact)
    edge = _edge("edge-1", "record-a", "record-b")

    result_single = compute_graph_signals((record_a, record_b), edges=(edge,))
    result_double = compute_graph_signals(
        (record_a, record_b), edges=(edge, edge)
    )

    assert result_single == result_double


def test_dangling_source_is_ignored() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    record_a = _record("record-a", artifact)
    edge = _edge("edge-1", "record-missing", "record-a")

    result = compute_graph_signals((record_a,), edges=(edge,))

    assert result.get("record-a", 0.0) == 0.0


def test_dangling_target_is_ignored() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    record_a = _record("record-a", artifact)
    edge = _edge("edge-1", "record-a", "record-missing")

    result = compute_graph_signals((record_a,), edges=(edge,))

    assert result.get("record-a", 0.0) == 0.0


def test_self_loop_is_conservative() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    record_a = _record("record-a", artifact)
    edge = _edge("edge-1", "record-a", "record-a")

    result = compute_graph_signals((record_a,), edges=(edge,))

    assert result.get("record-a", 0.0) == 0.0


def test_cycle_is_bounded_and_deterministic() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    records = tuple(
        _record(f"record-{index}", artifact) for index in range(3)
    )
    edges = (
        _edge("edge-1", "record-0", "record-1"),
        _edge("edge-2", "record-1", "record-2"),
        _edge("edge-3", "record-2", "record-0"),
    )

    result = compute_graph_signals(records, edges=edges)

    for record_id in ("record-0", "record-1", "record-2"):
        assert record_id in result
        assert 0.0 <= result[record_id] <= 1.0


def test_unknown_edge_type_is_conservative() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    record_a = _record("record-a", artifact)
    record_b = _record("record-b", artifact)
    edge = _edge("edge-1", "record-a", "record-b", edge_type="unknown_type")

    result = compute_graph_signals((record_a, record_b), edges=(edge,))

    assert result.get("record-a", 0.0) == 0.0
    assert result.get("record-b", 0.0) == 0.0


def test_graph_edge_rejects_invalid_confidence() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    record_a = _record("record-a", artifact)
    record_b = _record("record-b", artifact)

    for bad_confidence in (float("nan"), float("inf"), float("-inf"), 1.5, -0.5):
        with pytest.raises(ValueError, match="confidence"):
            GraphEdge(
                schema_version="graph-edge/v1",
                edge_id="edge-bad",
                from_id="record-a",
                to_id="record-b",
                edge_type="contains",
                confidence=bad_confidence,
                inferred=False,
            )

    # Confidence 0.0 wird akzeptiert, trägt aber kein Signal.
    edge_zero = GraphEdge(
        schema_version="graph-edge/v1",
        edge_id="edge-zero",
        from_id="record-a",
        to_id="record-b",
        edge_type="contains",
        confidence=0.0,
        inferred=False,
    )
    result = compute_graph_signals((record_a, record_b), edges=(edge_zero,))
    assert result.get("record-a", 0.0) == 0.0
    assert result.get("record-b", 0.0) == 0.0


def test_malformed_edge_type_is_conservative() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    record_a = _record("record-a", artifact)
    record_b = _record("record-b", artifact)
    edge = _edge("edge-1", "record-a", "record-b", edge_type="unknown_type")

    result = compute_graph_signals((record_a, record_b), edges=(edge,))

    assert result.get("record-a", 0.0) == 0.0
    assert result.get("record-b", 0.0) == 0.0


def test_candidate_without_edges_receives_zero() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    record_a = _record("record-a", artifact)

    result = compute_graph_signals((record_a,), edges=())

    assert result.get("record-a", 0.0) == 0.0


def test_two_logically_identical_graphs_produce_identical_signals() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    records_a = tuple(
        _record(f"record-{index}", artifact) for index in range(4)
    )
    edges_a = (
        _edge("edge-1", "record-0", "record-1"),
        _edge("edge-2", "record-2", "record-3"),
    )
    records_b = tuple(
        _record(f"record-{index}", artifact) for index in range(4)
    )
    edges_b = (
        _edge("edge-2", "record-2", "record-3"),
        _edge("edge-1", "record-0", "record-1"),
    )

    result_a = compute_graph_signals(records_a, edges=edges_a)
    result_b = compute_graph_signals(records_b, edges=edges_b)

    assert result_a == result_b


def test_no_wall_clock_in_graph_signals() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    record_a = _record("record-a", artifact)
    edge = _edge("edge-1", "record-a", "record-a")

    first = compute_graph_signals((record_a,), edges=(edge,))
    second = compute_graph_signals((record_a,), edges=(edge,))

    assert first == second
