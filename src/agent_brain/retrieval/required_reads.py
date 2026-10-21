"""Required-Reads-Integration für Retrieval (Slice 7, Task 5).

Konsumiert die bestehenden produktneutralen Contracts
``RequiredReadsProfile`` und ``resolve_required_reads`` aus
``agent_brain.context.required_reads`` und liefert ein neutrales
Retrieval-Resultat. Keine Claire-Dateipfade, keine Host-Hardcodes,
keine neue fachliche Runtime-Abhängigkeit.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_brain.context.required_reads import (
    RequiredRead,
    RequiredReadsProfile,
    resolve_required_reads,
)


@dataclass(frozen=True, slots=True)
class RetrievalRequiredReadsResult:
    """Neutrales Ergebnis der Required-Reads-Auflösung für Retrieval."""

    required_reads: tuple[RequiredRead, ...]
    limitations: tuple[str, ...] = ()


def resolve_retrieval_required_reads(
    *,
    profile: RequiredReadsProfile,
    task_scope: str,
    operation_mode: str,
    target_issue: str | None = None,
    target_paths: tuple[str, ...] = (),
    target_symbols: tuple[str, ...] = (),
    target_concepts: tuple[str, ...] = (),
    available_paths: frozenset[str] | None = None,
) -> RetrievalRequiredReadsResult:
    """Löst Required Reads für eine Retrieval-Anfrage auf.

    Delegiert vollständig an den bestehenden, produktneutralen
    Resolver. Keine Claire-Dateilisten, keine Repo-Hardcodes.
    """
    if not isinstance(profile, RequiredReadsProfile):
        raise TypeError("profile must be a RequiredReadsProfile")

    reads = resolve_required_reads(
        profile=profile,
        task_scope=task_scope,
        operation_mode=operation_mode,
        target_issue=target_issue,
        target_paths=target_paths,
        target_symbols=target_symbols,
        target_concepts=target_concepts,
        available_paths=available_paths,
    )

    limitations: list[str] = []
    if not reads:
        limitations.append("required_reads_profile_empty")
    if any(not read.available for read in reads):
        limitations.append("required_reads_not_all_available")

    return RetrievalRequiredReadsResult(
        required_reads=reads,
        limitations=tuple(limitations),
    )
