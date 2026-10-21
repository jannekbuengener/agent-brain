"""Deterministischer Hybrid-Ranking-Core (Slice 7, Task 3).

Berechnet aus vorhandenen RetrievalCandidate-Objekten und einer
RetrievalPolicy einen deterministischen, erklärbaren Gesamtscore pro
Kandidat. Keine Graph-Traversal-Logik, keine Vector-Runtime, keine
Trust-/Evidence-Engine (#8-Grenze). Alle fehlenden oder ungültigen
Signale werden konservativ auf 0.0 gesetzt.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from agent_brain.core.source_priority import SourcePriority
from agent_brain.retrieval.contract import (
    RANKING_EXPLANATION_SCHEMA,
    RANKING_FACTOR_SCHEMA,
    RETRIEVAL_CANDIDATE_SCHEMA,
    RETRIEVAL_RESULT_SCHEMA,
    RankingExplanation,
    RankingFactor,
    RetrievalCandidate,
    RetrievalPolicy,
    RetrievalQuery,
)

_FACTOR_NAMES = (
    "lexical",
    "semantic",
    "graph",
    "source_priority",
    "evidence_provenance",
)


def _sanitize_score(value: float, field_name: str) -> float:
    """Ungültige Ranking-Signale konservativ auf 0.0 setzen."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    result = float(value)
    if not math.isfinite(result) or result < 0.0 or result > 1.0:
        return 0.0
    return result


def _aggregate_score(value: float) -> float:
    """Gültige Summen deterministisch auf den Result-Contract [0,1] begrenzen."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    result = float(value)
    if not math.isfinite(result):
        return 0.0
    return min(1.0, max(0.0, result))


def _normalize_source_priority(
    source_priority: SourcePriority | None, source_id: str
) -> float:
    """Quellen-Rang auf [0,1] normalisieren; unbekannt = 0.0."""
    if source_priority is None:
        return 0.0
    rank = source_priority.rank(source_id)
    if rank is None:
        return 0.0
    ordered = source_priority.ordered_sources
    total = len(ordered)
    if total <= 1:
        return 1.0 if rank == 0 else 0.0
    return 1.0 - (rank / (total - 1))


def _build_factor(
    factor_name: str,
    raw_value: float,
    weight: float,
    missing: bool,
    fallback: bool,
) -> RankingFactor:
    normalized = _sanitize_score(raw_value, f"{factor_name}.normalized_value")
    sanitized_weight = _sanitize_score(weight, f"{factor_name}.weight")
    contribution = _sanitize_score(
        normalized * sanitized_weight, f"{factor_name}.contribution"
    )
    return RankingFactor(
        schema_version=RANKING_FACTOR_SCHEMA,
        factor_name=factor_name,
        raw_value=_sanitize_score(raw_value, f"{factor_name}.raw_value"),
        normalized_value=normalized,
        weight=sanitized_weight,
        contribution=contribution,
        missing=missing,
        fallback=fallback,
    )


def rank_candidates(
    candidates: Sequence[RetrievalCandidate],
    policy: RetrievalPolicy,
    *,
    source_priority: SourcePriority | None = None,
    graph_signals: Mapping[str, float] | None = None,
    lexical_signals: Mapping[str, float] | None = None,
) -> tuple[tuple[RetrievalCandidate, RankingExplanation], ...]:
    """Kandidaten deterministisch ranken und strukturierte Erklärungen erzeugen.

    Score = Summe(normalisierter Faktorwert * Gewicht) über alle fünf
    Faktor-Familien. Fehlende/ungültige Signale tragen 0.0 bei.
    Sortierschluessel: (-Gesamtscore, record_id aufsteigend).
    """
    if not isinstance(candidates, (tuple, list)) or not all(
        isinstance(item, RetrievalCandidate) for item in candidates
    ):
        raise TypeError("candidates must contain RetrievalCandidate values")
    if not isinstance(policy, RetrievalPolicy):
        raise TypeError("policy must be a RetrievalPolicy")
    if graph_signals is not None and not isinstance(graph_signals, Mapping):
        raise TypeError("graph_signals must be a mapping when present")
    if lexical_signals is not None and not isinstance(lexical_signals, Mapping):
        raise TypeError("lexical_signals must be a mapping when present")

    weights = dict(policy.factor_weights)
    graph_signals = graph_signals or {}
    lexical_signals = lexical_signals or {}

    ranked: list[tuple[RetrievalCandidate, RankingExplanation]] = []

    for candidate in candidates:
        source_id = candidate.artifact_ref.source_id
        record_id = candidate.record_id

        lexical_raw = _sanitize_score(
            lexical_signals.get(record_id, 0.0), "lexical.raw_value"
        )
        lexical_missing = record_id not in lexical_signals
        lexical_factor = _build_factor(
            "lexical",
            lexical_raw,
            weights.get("lexical", 0.0),
            missing=lexical_missing,
            fallback=lexical_missing,
        )

        semantic_factor = _build_factor(
            "semantic",
            0.0,
            weights.get("semantic", 0.0),
            missing=True,
            fallback=True,
        )

        graph_raw = _sanitize_score(
            graph_signals.get(record_id, 0.0), "graph.raw_value"
        )
        graph_missing = record_id not in graph_signals
        graph_factor = _build_factor(
            "graph",
            graph_raw,
            weights.get("graph", 0.0),
            missing=graph_missing,
            fallback=graph_missing,
        )

        sp_raw = _normalize_source_priority(source_priority, source_id)
        sp_missing = source_priority is None or source_priority.rank(source_id) is None
        source_priority_factor = _build_factor(
            "source_priority",
            sp_raw,
            weights.get("source_priority", 0.0),
            missing=sp_missing,
            fallback=sp_missing,
        )

        evidence_provenance_factor = _build_factor(
            "evidence_provenance",
            0.0,
            weights.get("evidence_provenance", 0.0),
            missing=True,
            fallback=True,
        )

        factors = (
            lexical_factor,
            semantic_factor,
            graph_factor,
            source_priority_factor,
            evidence_provenance_factor,
        )

        total_score = _aggregate_score(sum(f.contribution for f in factors))

        explanation = RankingExplanation(
            schema_version=RANKING_EXPLANATION_SCHEMA,
            candidate_id=candidate.candidate_id,
            total_score=total_score,
            factors=factors,
            missing_factors=tuple(f.factor_name for f in factors if f.missing),
            fallbacks=tuple(f.factor_name for f in factors if f.fallback),
            source_refs=(candidate.record_id,),
            graph_refs=(),
        )

        ranked_candidate = RetrievalCandidate(
            schema_version=RETRIEVAL_CANDIDATE_SCHEMA,
            candidate_id=candidate.candidate_id,
            record_id=candidate.record_id,
            artifact_ref=candidate.artifact_ref,
            score=total_score,
            factors=factors,
        )

        ranked.append((ranked_candidate, explanation))

    ranked.sort(key=lambda item: (-item[0].score, item[0].record_id))
    return tuple(ranked)


def build_retrieval_result(
    query: RetrievalQuery,
    ranked: Sequence[tuple[RetrievalCandidate, RankingExplanation]],
    *,
    stop_applied: bool = False,
    impact_applied: bool = False,
    limitations: tuple[str, ...] = (),
) -> object:
    """Bau ein RetrievalResult aus dem gerankten Output."""
    from agent_brain.retrieval.contract import RetrievalResult

    total_score = _aggregate_score(sum(exp.total_score for _, exp in ranked))

    return RetrievalResult(
        schema_version=RETRIEVAL_RESULT_SCHEMA,
        result_id=f"result_{query.query_id}",
        query_id=query.query_id,
        candidates=tuple(cand for cand, _ in ranked),
        total_score=total_score,
        explanation=tuple(exp for _, exp in ranked),
        stop_applied=stop_applied,
        impact_applied=impact_applied,
        limitations=limitations,
    )
