"""Annotierender Impact Radar (Slice 7, Task 4).

Der Impact Radar ist ausschließlich annotierend: Er macht strukturelle
Nähe sichtbar und aggregiert vorhandene Graph-Signale pro Kandidat.
Er autorisiert keine Entscheidungen, vergibt kein Trust, resolvt keine
Claims und implementiert keine Stop-Policy (#8-/ #10-Grenze).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from agent_brain.contracts import GraphEdge
from agent_brain.retrieval.contract import (
    RetrievalCandidate,
    RetrievalImpact,
    RetrievalPolicy,
)

_UNKNOWN_EDGE_TYPE = "unknown"


def _collect_edge_types(
    edges: Sequence[GraphEdge], record_id: str
) -> tuple[str, ...]:
    """Stabile, sortierte Edge-Typen für einen Record."""
    seen: set[str] = set()
    result: list[str] = []
    for edge in sorted(edges, key=lambda item: (item.edge_id, item.from_id, item.to_id)):
        if edge.from_id != record_id and edge.to_id != record_id:
            continue
        if edge.edge_type not in seen:
            seen.add(edge.edge_type)
            result.append(edge.edge_type)
    return tuple(result)


def annotate_impact(
    candidates: Sequence[RetrievalCandidate],
    graph_signals: Mapping[str, float] = (),
    edges: Sequence[GraphEdge] = (),
    policy: RetrievalPolicy | None = None,
) -> tuple[RetrievalImpact, ...]:
    """Annotiert Kandidaten mit Impact-Radar-Informationen.

    Für jeden Candidate wird eine RetrievalImpact erzeugt:
    - signal_value: aus graph_signals, andernfalls 0.0
    - graph_distance: 0 bei keinem Signal, sonst 1 (direkte Nachbarschaft)
    - edge_types: beteiligte Edge-Typen des Kandidaten
    - impact_id / candidate_id: stabile Identitäten

    Keine Trust-, Decision- oder Claim-Semantik.
    """
    if not isinstance(candidates, (tuple, list)) or not all(
        isinstance(item, RetrievalCandidate) for item in candidates
    ):
        raise TypeError("candidates must contain RetrievalCandidate values")
    if graph_signals is not None and not isinstance(graph_signals, Mapping):
        raise TypeError("graph_signals must be a mapping when present")
    if (edges is not None and not isinstance(edges, (tuple, list))) or not all(
        isinstance(item, GraphEdge) for item in edges
    ):
        raise TypeError("edges must contain GraphEdge values")

    impacts: list[RetrievalImpact] = []
    for candidate in sorted(candidates, key=lambda item: item.record_id):
        record_id = candidate.record_id
        signal_value = _sanitize_signal(graph_signals.get(record_id, 0.0))
        edge_types = _collect_edge_types(edges, record_id)
        graph_distance = 0 if signal_value == 0.0 else 1

        impact = RetrievalImpact(
            schema_version="retrieval-impact/v1",
            impact_id=f"impact_{candidate.candidate_id}",
            candidate_id=candidate.candidate_id,
            graph_distance=graph_distance,
            edge_types=edge_types,
            signal_value=signal_value,
        )
        impacts.append(impact)

    return tuple(impacts)


def _sanitize_signal(value: float, field_name: str = "signal_value") -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    result = float(value)
    if not math.isfinite(result) or result < 0.0 or result > 1.0:
        return 0.0
    return result
