"""Neutral Slice-6 knowledge snapshot -> Slice-7 retrieval acceptance path."""

from __future__ import annotations

import json
from pathlib import Path

from agent_brain.contracts import GraphEdge, IndexRecord
from agent_brain.core.source_priority import SourcePriority
from agent_brain.knowledge.serialization import parse_knowledge_snapshot
from agent_brain.retrieval import (
    RetrievalPolicy,
    RetrievalQuery,
    compute_graph_signals,
    run_retrieval,
)

FIXTURE_ROOT = Path("tests/fixtures")
KNOWLEDGE_SNAPSHOT = FIXTURE_ROOT / "knowledge" / "knowledge_snapshot.neutral.v1.json"
RETRIEVAL_INDEX = FIXTURE_ROOT / "retrieval" / "neutral_index.neutral.v1.json"
RETRIEVAL_EDGES = FIXTURE_ROOT / "retrieval" / "neutral_edges.neutral.v1.json"


def _policy() -> RetrievalPolicy:
    return RetrievalPolicy(
        schema_version="retrieval-policy/v1",
        policy_id="neutral-fixture-policy",
        factor_weights={
            "lexical": 0.4,
            "semantic": 0.2,
            "graph": 0.2,
            "source_priority": 0.1,
            "evidence_provenance": 0.1,
        },
        default_factor_value=0.0,
        tie_break_keys=("record_id",),
        source_priority=("source-widgets",),
    )


def _query() -> RetrievalQuery:
    return RetrievalQuery(
        schema_version="retrieval-query/v1",
        query_id="neutral-fixture-query",
        query_text="build widget",
        source_id="source-widgets",
    )


def _load_retrieval_inputs() -> tuple[tuple[IndexRecord, ...], tuple[GraphEdge, ...]]:
    index_payload = json.loads(RETRIEVAL_INDEX.read_text(encoding="utf-8"))
    edge_payload = json.loads(RETRIEVAL_EDGES.read_text(encoding="utf-8"))
    records = tuple(IndexRecord.from_dict(entry) for entry in index_payload["records"])
    edges = tuple(GraphEdge.from_dict(entry) for entry in edge_payload["edges"])
    return records, edges


def test_slice6_snapshot_supports_reproducible_neutral_retrieval() -> None:
    snapshot = parse_knowledge_snapshot(KNOWLEDGE_SNAPSHOT.read_text(encoding="utf-8"))
    records, edges = _load_retrieval_inputs()

    manifests = {manifest.source_ref: manifest.source_hash for manifest in snapshot.manifests}
    assert manifests
    for record in records:
        source_path = record.source.source_path
        assert source_path in manifests
        assert record.source.source_hash == manifests[source_path]

    graph_signals = compute_graph_signals(records, edges)
    source_priority = SourcePriority(ordered_sources=("source-widgets",))

    first = run_retrieval(
        query=_query(),
        records=records,
        edges=edges,
        policy=_policy(),
        source_priority=source_priority,
        graph_signals=graph_signals,
    )
    second_records = tuple(reversed(records))
    second_edges = tuple(reversed(edges))
    second = run_retrieval(
        query=_query(),
        records=second_records,
        edges=second_edges,
        policy=_policy(),
        source_priority=source_priority,
        graph_signals=compute_graph_signals(second_records, second_edges),
    )

    assert first == second
    assert len(first.candidates) == 3
    assert first.stop_applied is False
    assert first.impact_applied is True
    assert [candidate.record_id for candidate in first.candidates] == [
        candidate.record_id for candidate in second.candidates
    ]
