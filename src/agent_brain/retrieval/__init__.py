"""Retrieval boundary — öffentliche Slice-7-Surface.

Produktneutrale Hybrid-Retrieval- und Knowledge-Reasoning-Komponente.
Keine Claire-, Trading- oder SurrealDB-Abhängigkeit. Alle Typen und
Funktionen sind deterministisch, side-effect-free und testbar über
neutrale #16-Knowledge-Fixtures.
"""

from __future__ import annotations

from agent_brain.core.source_priority import SourcePriority
from agent_brain.retrieval.contract import (
    RANKING_EXPLANATION_SCHEMA,
    RANKING_FACTOR_SCHEMA,
    RETRIEVAL_CANDIDATE_SCHEMA,
    RETRIEVAL_IMPACT_SCHEMA,
    RETRIEVAL_POLICY_SCHEMA,
    RETRIEVAL_QUERY_SCHEMA,
    RETRIEVAL_RESULT_SCHEMA,
    RETRIEVAL_STOP_SCHEMA,
    RankingExplanation,
    RankingFactor,
    RetrievalCandidate,
    RetrievalImpact,
    RetrievalPolicy,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStop,
)
from agent_brain.retrieval.graph_signals import (
    bounded_graph_traversal,
    compute_graph_signals,
)
from agent_brain.retrieval.impact_radar import annotate_impact
from agent_brain.retrieval.ranking import (
    build_retrieval_result,
    rank_candidates,
)
from agent_brain.retrieval.required_reads import (
    RetrievalRequiredReadsResult,
    resolve_retrieval_required_reads,
)
from agent_brain.retrieval.retriever import (
    collect_candidates,
    run_retrieval,
)
from agent_brain.retrieval.stop_resolver import resolve_retrieval_stop

__all__ = [
    "RANKING_EXPLANATION_SCHEMA",
    "RANKING_FACTOR_SCHEMA",
    "RETRIEVAL_CANDIDATE_SCHEMA",
    "RETRIEVAL_IMPACT_SCHEMA",
    "RETRIEVAL_POLICY_SCHEMA",
    "RETRIEVAL_QUERY_SCHEMA",
    "RETRIEVAL_RESULT_SCHEMA",
    "RETRIEVAL_STOP_SCHEMA",
    "RankingExplanation",
    "RankingFactor",
    "RetrievalCandidate",
    "RetrievalImpact",
    "RetrievalPolicy",
    # Contracts
    "RetrievalQuery",
    "RetrievalRequiredReadsResult",
    "RetrievalResult",
    "RetrievalStop",
    "SourcePriority",
    # Impact Radar
    "annotate_impact",
    "bounded_graph_traversal",
    "build_retrieval_result",
    "collect_candidates",
    # Graph
    "compute_graph_signals",
    # Ranking
    "rank_candidates",
    # Required Reads
    "resolve_retrieval_required_reads",
    # Stop Resolver
    "resolve_retrieval_stop",
    # Orchestrierung
    "run_retrieval",
]
