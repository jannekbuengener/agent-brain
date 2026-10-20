from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_brain.contracts.index import GraphEdge, IndexRecord, graph_fingerprint

FIXTURE = Path("tests/fixtures/contracts/index_graph.neutral.v1.json")


def _load_fixture() -> tuple[list[IndexRecord], list[GraphEdge]]:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    records = [IndexRecord.from_dict(item) for item in payload["records"]]
    edges = [GraphEdge.from_dict(item) for item in payload["edges"]]
    return records, edges


def test_index_graph_fixture_round_trip() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    records, edges = _load_fixture()

    assert [record.to_dict() for record in records] == payload["records"]
    assert [edge.to_dict() for edge in edges] == payload["edges"]


def test_graph_fingerprint_is_stable_for_reordered_equivalent_inputs() -> None:
    records, edges = _load_fixture()

    assert graph_fingerprint(records, edges) == graph_fingerprint(
        list(reversed(records)),
        list(reversed(edges)),
    )


def test_graph_fingerprint_changes_when_structure_changes() -> None:
    records, edges = _load_fixture()
    changed = GraphEdge.from_dict(
        {
            **edges[0].to_dict(),
            "to_id": "record-other",
        }
    )

    assert graph_fingerprint(records, edges) != graph_fingerprint(records, [changed])


def test_index_record_ignores_unknown_additive_v1_fields() -> None:
    records, _ = _load_fixture()
    payload = records[0].to_dict()
    payload["future_optional_field"] = "ignored"

    restored = IndexRecord.from_dict(payload)

    assert "future_optional_field" not in restored.to_dict()


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        (
            {
                "schema_version": "index-record/v1",
                "record_id": " ",
                "record_type": "module",
                "source": {
                    "schema_version": "artifact-ref/v1",
                    "artifact_id": "artifact-example",
                    "source_id": "source-example",
                    "source_path": "src/widget.py",
                    "source_hash": "a" * 64,
                },
            },
            "record_id",
        ),
        (
            {
                "schema_version": "index-record/v1",
                "record_id": "record-example",
                "record_type": " ",
                "source": {
                    "schema_version": "artifact-ref/v1",
                    "artifact_id": "artifact-example",
                    "source_id": "source-example",
                    "source_path": "src/widget.py",
                    "source_hash": "a" * 64,
                },
            },
            "record_type",
        ),
        (
            {
                "schema_version": "graph-edge/v1",
                "edge_id": "edge-example",
                "from_id": " ",
                "to_id": "record-b",
                "edge_type": "contains",
            },
            "from_id",
        ),
        (
            {
                "schema_version": "graph-edge/v1",
                "edge_id": "edge-example",
                "from_id": "record-a",
                "to_id": "record-b",
                "edge_type": " ",
            },
            "edge_type",
        ),
    ],
)
def test_index_graph_contracts_reject_blank_required_fields(payload, field: str) -> None:
    factory = GraphEdge.from_dict if payload["schema_version"].startswith("graph-edge") else IndexRecord.from_dict
    with pytest.raises(ValueError, match=field):
        factory(payload)


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_graph_edge_rejects_confidence_outside_unit_interval(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        GraphEdge(
            schema_version="graph-edge/v1",
            edge_id="edge-example",
            from_id="record-a",
            to_id="record-b",
            edge_type="contains",
            confidence=confidence,
        )
