"""Retrieval-Orchestrierung (Slice 7, Task 6).

Verbindet Candidate Collection, Graph-Signale, Ranking, Impact,
Required-Reads-Zustand und Policy/Stop zu einer deterministischen,
produktneutralen Retrieval-Anfrage. Keine SurrealDB, keine
Netzwerkzugriffe, keine Claire-/Trading-Abhängigkeit.
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
from agent_brain.retrieval.graph_signals import compute_graph_signals
from agent_brain.retrieval.impact_radar import annotate_impact
from agent_brain.retrieval.ranking import build_retrieval_result, rank_candidates
from agent_brain.retrieval.required_reads import RetrievalRequiredReadsResult
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


def _stable_limitations(*groups: Sequence[str]) -> tuple[str, ...]:
    """Limitations in stabiler Einfügereihenfolge deduplizieren."""
    seen: set[str] = set()
    result: list[str] = []
    for group in groups:
        for item in group:
            if item not in seen:
                seen.add(item)
                result.append(item)
    return tuple(result)


def _required_read_state(
    query: RetrievalQuery,
    result: RetrievalRequiredReadsResult | None,
) -> tuple[bool, tuple[str, ...], tuple[str, ...]]:
    """Neutrale Required-Read-Verfügbarkeit für Policy und Result ableiten."""
    limitations = tuple(result.limitations) if result is not None else ()
    required_paths = tuple(query.required_reads)

    if result is None:
        if not required_paths:
            return True, (), limitations
        return False, tuple(sorted(set(required_paths))), _stable_limitations(
            limitations, ("required_reads_unresolved",)
        )

    reads_by_path = {read.path: read for read in result.required_reads}
    if required_paths:
        unavailable = tuple(
            sorted(
                path
                for path in set(required_paths)
                if path not in reads_by_path or not reads_by_path[path].available
            )
        )
    else:
        unavailable = tuple(
            sorted(read.path for read in result.required_reads if not read.available)
        )
    return not unavailable, unavailable, limitations


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
    allowed_record_types = frozenset(query.record_type_filter) if query is not None else frozenset()
    candidates: list[RetrievalCandidate] = []
    for record in unique_records:
        if allowed_record_types and record.record_type not in allowed_record_types:
            continue
        candidates.append(
            RetrievalCandidate(
                schema_version="retrieval-candidate/v1",
                candidate_id=f"cand_{record.record_id}",
                record_id=record.record_id,
                artifact_ref=record.source,
                score=0.0,
                factors=(),
            )
        )
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
    required_reads_result: RetrievalRequiredReadsResult | None = None,
) -> RetrievalResult:
    """Führe eine vollständige, deterministische Retrieval-Anfrage aus.

    Required Reads liefern neutralen Zustand und Limitations. Eine injizierte
    Policy entscheidet anhand dieses Zustands, ob Retrieval gestoppt wird.
    Ohne Policy wird aus fehlenden Required Reads keine neue Produktregel
    erfunden; die Einschränkung bleibt im Result sichtbar.
    """
    if not isinstance(query, RetrievalQuery):
        raise TypeError("query must be a RetrievalQuery")
    if not isinstance(policy, RetrievalPolicy):
        raise TypeError("policy must be a RetrievalPolicy")
    if required_reads_result is not None and not isinstance(
        required_reads_result, RetrievalRequiredReadsResult
    ):
        raise TypeError(
            "required_reads_result must be a RetrievalRequiredReadsResult when present"
        )

    required_reads_available, unavailable_reads, limitations = _required_read_state(
        query, required_reads_result
    )

    if stop_hook is not None:
        stop = resolve_retrieval_stop(
            policy_hook=stop_hook,
            operation="retrieval.read",
            context_attributes={
                "query_id": query.query_id,
                "source_id": query.source_id,
                "required_reads_available": required_reads_available,
                "required_reads_unavailable": unavailable_reads,
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
                limitations=_stable_limitations(
                    limitations, (f"stop_applied: {stop.reason}",)
                ),
            )

    candidates = collect_candidates(records=records, edges=edges, query=query)

    candidate_ids = {candidate.record_id for candidate in candidates}
    graph_records = tuple(
        record for record in _dedupe_and_sort(records) if record.record_id in candidate_ids
    )
    effective_graph_signals = (
        dict(graph_signals)
        if graph_signals is not None
        else compute_graph_signals(graph_records, edges)
    )

    ranked = rank_candidates(
        candidates=candidates,
        policy=policy,
        source_priority=source_priority,
        graph_signals=effective_graph_signals,
        lexical_signals=lexical_signals or {},
    )
    ranked = ranked[: query.limit]

    impacts = annotate_impact(
        candidates=tuple(candidate for candidate, _ in ranked),
        graph_signals=effective_graph_signals,
        edges=edges,
        policy=policy,
    )

    return build_retrieval_result(
        query=query,
        ranked=ranked,
        stop_applied=False,
        impact_applied=bool(impacts),
        limitations=limitations,
    )
