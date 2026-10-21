"""Retrieval-Orchestrierung (Slice 7, Task 6).

Verbindet die Phasen collect → stop → rank → impact zu einer
deterministischen, produktneutralen Retrieval-Anfrage. Keine SurrealDB,
keine Netzwerkzugriffe, keine Claire-/Trading-Abhängigkeit.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from agent_brain.contracts import GraphEdge, IndexRecord
from agent_brain.core.policy import PolicyHook
from agent_brain.core.source_priority import SourcePriority
from agent_brain.retrieval.contract import (
    RetrievalCandidate,
    RetrievalPolicy,
    RetrievalQuery,
    RetrievalResult,
)
from agent_brain.retrieval.impact_radar import annotate_impact
from agent_brain.retrieval.ranking import build_retrieval_result, rank_candidates
from agent_brain.retrieval.stop_resolver import resolve_retrieval_stop


def _dedupe_and_sort(
    records: Sequence[IndexRecord],
) -> tuple[IndexRecord, ...]:
    """Deduplizieren nach record_id und stabil nach record_id sortieren."""
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
    """Sammle Retrieval-Kandidaten aus Index-Records deterministisch."""
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


def run_retrieval(
    query: RetrievalQuery,
    records: Sequence[IndexRecord],
    edges: Sequence[GraphEdge] = (),
    *,
    policy: RetrievalPolicy,
    source_priority: SourcePriority | None = None,
    graph_signals: Mapping[str, float] | None = None,
    lexical_signals: Mapping[str, float] | None = None,
    stop_hook: PolicyHook | None = None,
) -> RetrievalResult:
    """Führe eine vollständige, deterministische Retrieval-Anfrage aus.

    Phasen:
    1. Stop-Prüfung (falls stop_hook gegeben): allowed=False → früher,
       konservativer Abbruch mit leeren Kandidaten.
    2. Candidate Collection (Task 2): deterministisch, dedupliziert,
       stabil sortiert.
    3. Hybrid Ranking (Task 3): gewichtete Score-Komposition, totaler
       Tie-Break, strukturierte Explanation.
    4. Impact Radar (Task 4): annotierende Graph-Signale, keine
       Trust-/Decision-Semantik.

    Eingabe und Ausgabe verwenden ausschließlich die bestehenden
    #15-/Task-1-Contracts. Keine SurrealDB, kein Netzwerk, keine
    Claire-/Trading-Abhängigkeit.
    """
    if not isinstance(query, RetrievalQuery):
        raise TypeError("query must be a RetrievalQuery")
    if not isinstance(policy, RetrievalPolicy):
        raise TypeError("policy must be a RetrievalPolicy")

    # Phase 1: Stop-Prüfung (fail-conservative).
    stop_applied = False
    if stop_hook is not None:
        stop = resolve_retrieval_stop(
            policy_hook=stop_hook,
            operation="retrieval.read",
            context_attributes={
                "query_id": query.query_id,
                "source_id": query.source_id,
            },
        )
        if not stop.allowed:
            return RetrievalResult(
                schema_version="retrieval-result/v1",
                result_id=f"result_{query.query_id}",
                query_id=query.query_id,
                candidates=(),
                total_score=0.0,
                explanation=(),
                stop_applied=True,
                impact_applied=False,
                limitations=(f"stop_applied: {stop.reason}",),
            )
        stop_applied = True

    # Phase 2: Candidate Collection.
    candidates = collect_candidates(
        records=records,
        edges=edges,
        query=query,
    )

    # Phase 3: Hybrid Ranking + Explanation.
    ranked = rank_candidates(
        candidates=candidates,
        policy=policy,
        source_priority=source_priority,
        graph_signals=graph_signals or {},
        lexical_signals=lexical_signals or {},
    )

    # Phase 4: Impact Radar (annotierend).
    graph_signal_map = dict(graph_signals or {})
    annotate_impact(
        candidates=tuple(cand for cand, _ in ranked),
        graph_signals=graph_signal_map,
        edges=edges,
        policy=policy,
    )

    # RetrievalResult zusammenbauen.
    return build_retrieval_result(
        query=query,
        ranked=ranked,
        stop_applied=stop_applied,
        impact_applied=True,
        limitations=(),
    )
