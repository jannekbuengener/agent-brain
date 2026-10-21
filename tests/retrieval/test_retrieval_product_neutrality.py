"""Produktneutralitäts-Tests (Slice 7, Task 6).

Stellen sicher, dass der Retrieval-Core keine Claire-, Trading-,
Host- oder SurrealDB-Abhängigkeiten einführt und über neutrale
Fixtures vollständig testbar ist.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent_brain.contracts import ArtifactRef, GraphEdge, IndexRecord, RepositorySource
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


def test_core_imports_without_claire() -> None:
    import agent_brain.retrieval as mod

    source = mod.__file__ or ""
    assert "claire" not in source.lower()
    assert "trading" not in source.lower()
    assert "surrealdb" not in source.lower()


def test_no_host_paths_in_public_surface() -> None:
    import inspect

    import agent_brain.retrieval as mod

    source = inspect.getsource(mod)
    assert "C:" not in source
    assert "/home/" not in source
    assert "/Users/" not in source


def test_no_network_or_db_usage() -> None:
    import agent_brain.retrieval as mod

    source = mod.__file__ or ""
    assert "surreal" not in source.lower()
    assert "http" not in source.lower()
    assert "socket" not in source.lower()


def test_run_retrieval_returns_deterministic_result() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    records = (
        _record("record-zebra", artifact),
        _record("record-alpha", artifact),
    )
    edges = (
        _edge("edge-1", "record-zebra", "record-alpha"),
    )

    first = run_retrieval(
        query=_query(),
        records=records,
        edges=edges,
        policy=_policy(),
        source_priority=_source_priority(),
    )
    second = run_retrieval(
        query=_query(),
        records=records,
        edges=edges,
        policy=_policy(),
        source_priority=_source_priority(),
    )

    assert first == second
    assert first.query_id == "query-1"
    assert first.stop_applied is False
    assert first.impact_applied is True


def test_run_retrieval_input_reordering_identical() -> None:
    artifact = _artifact("artifact-widget", "a" * 64)
    records = tuple(
        _record(f"record-{index:03d}", artifact) for index in range(5)
    )
    reversed_records = tuple(reversed(records))

    first = run_retrieval(
        query=_query(),
        records=records,
        policy=_policy(),
        source_priority=_source_priority(),
    )
    second = run_retrieval(
        query=_query(),
        records=reversed_records,
        policy=_policy(),
        source_priority=_source_priority(),
    )

    assert [c.record_id for c in first.candidates] == [
        c.record_id for c in second.candidates
    ]
    assert first == second


def test_stop_hook_blocks_retrieval() -> None:
    class DenyingHook(PolicyHook):
        def evaluate(self, context) -> PolicyDecision:
            return PolicyDecision(allowed=False, reasons=("policy_denied",))

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


def test_neutral_index_fixture_loads() -> None:
    fixture = Path("tests/fixtures/retrieval/neutral_index.neutral.v1.json")
    assert fixture.exists()
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "index-record/v1"
    assert len(payload["records"]) == 3


def test_neutral_edges_fixture_loads() -> None:
    fixture = Path("tests/fixtures/retrieval/neutral_edges.neutral.v1.json")
    assert fixture.exists()
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "graph-edge/v1"
    assert len(payload["edges"]) == 2


def test_run_retrieval_against_neutral_fixtures() -> None:
    index_payload = json.loads(
        Path("tests/fixtures/retrieval/neutral_index.neutral.v1.json").read_text(
            encoding="utf-8"
        )
    )
    edges_payload = json.loads(
        Path("tests/fixtures/retrieval/neutral_edges.neutral.v1.json").read_text(
            encoding="utf-8"
        )
    )

    _source()
    records = tuple(
        IndexRecord.from_dict(entry) for entry in index_payload["records"]
    )
    edges = tuple(
        GraphEdge.from_dict(entry) for entry in edges_payload["edges"]
    )

    result = run_retrieval(
        query=_query(),
        records=records,
        edges=edges,
        policy=_policy(),
        source_priority=_source_priority(),
    )

    assert result.query_id == "query-1"
    assert len(result.candidates) == 3
    assert result.stop_applied is False
    assert result.impact_applied is True
    # Alle Kandidaten müssen eine deterministische candidate_id haben.
    assert all(c.candidate_id.startswith("cand_") for c in result.candidates)
    # Stabil sortiert nach record_id.
    record_ids = [c.record_id for c in result.candidates]
    assert record_ids == sorted(record_ids)


def test_run_retrieval_zero_candidates() -> None:
    result = run_retrieval(
        query=_query(),
        records=(),
        edges=(),
        policy=_policy(),
        source_priority=_source_priority(),
    )

    assert result.candidates == ()
    assert result.total_score == 0.0
    assert result.explanation == ()
    assert result.stop_applied is False
