"""Produktneutrale Graph-/Struktur-Signale (Slice 7, Task 4).

Berechnet deterministische Graph-Signale aus bestehenden GraphEdge-
Contracts. Keine Ranking-Gewichte, keine Trust-/Decision-Semantik (#8),
keine SurrealDB (#10). Alle fehlenden oder ungültigen Signale werden
konservativ auf 0.0 gesetzt.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from agent_brain.contracts import GraphEdge, IndexRecord

_BOUND_TRAVERSAL_MAX_DEPTH = 2

_KNOWN_EDGE_TYPES = frozenset(
    {
        "contains",
        "references",
        "cites",
        "depends_on",
        "part_of",
        "defines",
        "uses",
    }
)


def _sanitize_confidence(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    result = float(value)
    if math.isnan(result) or math.isinf(result):
        return 0.0
    if result < 0.0 or result > 1.0:
        return 0.0
    return result


def _dedupe_edges(edges: Sequence[GraphEdge]) -> tuple[GraphEdge, ...]:
    """Deduplizieren nach (from_id, to_id, edge_type), stabil sortiert."""
    seen: set[tuple[str, str, str]] = set()
    deduped: list[GraphEdge] = []
    for edge in sorted(edges, key=lambda item: (item.edge_id, item.from_id, item.to_id)):
        key = (edge.from_id, edge.to_id, edge.edge_type)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(edge)
    return tuple(deduped)


def compute_graph_signals(
    records: Sequence[IndexRecord],
    edges: Sequence[GraphEdge] = (),
) -> dict[str, float]:
    """Berechnet deterministische Graph-Signale pro Record-ID.

    Jeder Record erhält einen Signalwert in [0,1], der den
    gewichteten Durchschnitt der zugehörigen gültigen Kanten widerspiegelt.
    Records ohne valide Kanten erhalten 0.0.

    Regeln:
    - Gerichtete Semantik (from_id → to_id).
    - Nur bekannte Edge-Typen tragen bei.
    - Dangling source/target werden ignoriert.
    - Self-Loops tragen nicht bei.
    - Ungültige Confidence (NaN/Inf/außerhalb [0,1]) trägt nicht bei.
    - Duplicate Edges werden einmal gezählt.
    - Cycle-Sicher: keine ungebundene Traversal, feste Max-Tiefe.
    - Deterministisch: Sortierung über stabile IDs.
    """
    if not isinstance(records, (tuple, list)) or not all(
        isinstance(item, IndexRecord) for item in records
    ):
        raise TypeError("records must contain IndexRecord values")
    if not isinstance(edges, (tuple, list)) or not all(
        isinstance(item, GraphEdge) for item in edges
    ):
        raise TypeError("edges must contain GraphEdge values")

    record_ids: set[str] = {record.record_id for record in records}
    signals: dict[str, float] = {record_id: 0.0 for record_id in record_ids}
    accumulators: dict[str, list[float]] = {record_id: [] for record_id in record_ids}

    unique_edges = _dedupe_edges(edges)

    for edge in unique_edges:
        # Bekannter Edge-Typ?
        if edge.edge_type not in _KNOWN_EDGE_TYPES:
            continue
        # Dangling source/target?
        if edge.from_id not in record_ids or edge.to_id not in record_ids:
            continue
        # Self-Loop?
        if edge.from_id == edge.to_id:
            continue
        # Confidence valid?
        confidence = _sanitize_confidence(edge.confidence, f"edge {edge.edge_id}")
        if confidence == 0.0:
            continue

        accumulators[edge.from_id].append(confidence)
        accumulators[edge.to_id].append(confidence)

    for record_id in record_ids:
        values = accumulators[record_id]
        if not values:
            signals[record_id] = 0.0
        else:
            avg = sum(values) / len(values)
            signals[record_id] = min(1.0, max(0.0, avg))

    return signals


def bounded_graph_traversal(
    start_id: str,
    edges: Sequence[GraphEdge],
    *,
    max_depth: int = _BOUND_TRAVERSAL_MAX_DEPTH,
) -> tuple[str, ...]:
    """Bounded, deterministische Traversal vom Start-Knoten.

    Gibt alle erreichbaren Knoten-IDs bis max_depth zurück, sortiert.
    Zyklen werden durch einen visited-set abgebrochen.
    """
    if max_depth < 0:
        return ()

    adjacency: dict[str, list[str]] = {}
    for edge in sorted(edges, key=lambda item: (item.from_id, item.to_id)):
        adjacency.setdefault(edge.from_id, []).append(edge.to_id)

    visited: set[str] = {start_id}
    frontier: list[str] = [start_id]
    depth = 0

    while frontier and depth < max_depth:
        next_frontier: list[str] = []
        for node in frontier:
            for neighbor in adjacency.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.append(neighbor)
        frontier = next_frontier
        depth += 1

    return tuple(sorted(visited - {start_id}))
