"""Deterministische Retrieval-Kandidaten-Sammlung (Slice 7, Task 2).

Die collect-Phase baut RetrievalCandidate-Objekte aus den bestehenden
#15-Contracts (IndexRecord, GraphEdge, ArtifactRef). Es wird keine
Ranking-Semantik vorgenommen: alle Kandidaten erhalten zunächst Score 0.0
und keine Faktoren. Die Ausgabe ist deterministisch und stabil sortiert,
unabh‰ngig von der Eingangsreihenfolge.
"""

from __future__ import annotations

from collections.abc import Sequence

from agent_brain.contracts import GraphEdge, IndexRecord
from agent_brain.retrieval.contract import RetrievalCandidate, RetrievalQuery


def _dedupe_and_sort(
    records: Sequence[IndexRecord],
) -> tuple[IndexRecord, ...]:
    """Deduplizieren nach record_id und stabil nach record_id sortieren.

    Vor der Deduplikation wird sortiert, damit das Ergebnis unabh‰ngig
    von der Eingangsreihenfolge, dict-/set-Iteration und
    Dateisystem-Reihenfolge ist.
    """
    ordered = sorted(records, key=lambda item: (item.record_id, item.source.artifact_id))
    seen: set[str] = set()
    deduped: list[IndexRecord] = []
    for record in ordered:
        if record.record_id in seen:
            continue
        seen.add(record.record_id)
        deduped.append(record)
    return tuple(deduped)


def collect_candidates(
    records: Sequence[IndexRecord],
    edges: Sequence[GraphEdge] = (),
    *,
    query: RetrievalQuery | None = None,
) -> tuple[RetrievalCandidate, ...]:
    """Sammle Retrieval-Kandidaten aus Index-Records deterministisch.

    - Jeder IndexRecord wird zu einem RetrievalCandidate (Score 0.0,
      keine Faktoren) – Ranking folgt in Task 3.
    - Deduplikation nach record_id.
    - Stabil sortiert nach record_id (Tie-Break: artifact_id).
    - GraphEdges werden entgegengenommen, beeinflussen die Sammlung in
      dieser Phase aber nicht (Graph-Signale folgen in Task 4).
    """
    if not isinstance(records, (tuple, list)) or not all(
        isinstance(item, IndexRecord) for item in records
    ):
        raise TypeError("records must contain IndexRecord values")
    if not isinstance(edges, (tuple, list)) or not all(
        isinstance(item, GraphEdge) for item in edges
    ):
        raise TypeError("edges must contain GraphEdge values")
    if query is not None and not isinstance(query, RetrievalQuery):
        raise TypeError("query must be a RetrievalQuery when present")

    unique_records = _dedupe_and_sort(records)
    candidates: list[RetrievalCandidate] = []
    for record in unique_records:
        candidate = RetrievalCandidate(
            schema_version="retrieval-candidate/v1",
            candidate_id=f"cand_{record.record_id}",
            record_id=record.record_id,
            artifact_ref=record.source,
            score=0.0,
            factors=(),
        )
        candidates.append(candidate)
    return tuple(candidates)
