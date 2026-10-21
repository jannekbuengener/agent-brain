"""Impact radar tests (Slice 7, Task 4).

RED-first: Diese Tests definieren das erwartete Verhalten des
annotierenden Impact Radar und müssen vor der Implementierung
fehlschlagen.
"""

from __future__ import annotations

from agent_brain.contracts import ArtifactRef, GraphEdge, IndexRecord
from agent_brain.retrieval.contract import RetrievalCandidate, RetrievalPolicy
from agent_brain.retrieval.impact_radar import annotate_impact


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


def _candidate(
    record_id: str,
    artifact: ArtifactRef,
    score: float = 0.0,
) -> RetrievalCandidate:
    return RetrievalCandidate(
        schema_version="retrieval-candidate/v1",
        candidate_id=f"cand_{record_id}",
        record_id=record_id,
        artifact_ref=artifact,
        score=score,
        factors=(),
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


def test_impact_radar_empty_graph_annotates_conservatively() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    candidate = _candidate("record-a", artifact)

    impacts = annotate_impact((candidate,), graph_signals={}, policy=_policy())

    assert len(impacts) == 1
    assert impacts[0].candidate_id == "cand_record-a"
    assert impacts[0].graph_distance == 0
    assert impacts[0].signal_value == 0.0
    assert impacts[0].edge_types == ()


def test_impact_radar_annotates_graph_signal() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    _record("record-a", artifact)
    _record("record-b", artifact)
    _edge("edge-1", "record-a", "record-b")

    candidates = (
        _candidate("record-a", artifact),
        _candidate("record-b", artifact),
    )
    graph_signals = {"record-a": 0.5, "record-b": 0.3}

    impacts = annotate_impact(candidates, graph_signals=graph_signals, policy=_policy())

    by_id = {impact.candidate_id: impact for impact in impacts}
    assert by_id["cand_record-a"].signal_value == 0.5
    assert by_id["cand_record-b"].signal_value == 0.3


def test_impact_radar_no_positive_invention_for_missing() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    candidate = _candidate("record-a", artifact)

    impacts = annotate_impact((candidate,), graph_signals={}, policy=_policy())

    assert impacts[0].signal_value == 0.0


def test_impact_radar_is_deterministic() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    candidate = _candidate("record-a", artifact)

    first = annotate_impact((candidate,), graph_signals={}, policy=_policy())
    second = annotate_impact((candidate,), graph_signals={}, policy=_policy())

    assert first == second


def test_impact_radar_no_trust_or_decision_semantics() -> None:
    import agent_brain.retrieval.impact_radar as mod

    source = mod.__file__ or ""
    assert "trust" not in source.lower()
    assert "decision" not in source.lower()
    assert "claim" not in source.lower()
    assert "surrealdb" not in source.lower()
