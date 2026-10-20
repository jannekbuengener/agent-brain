"""Injected source-priority ordering without built-in repository names."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourcePriority:
    """Rank caller-supplied source names from strongest to weakest."""

    ordered_sources: tuple[str, ...]

    def __post_init__(self) -> None:
        normalized = tuple(source.strip() for source in self.ordered_sources)
        if any(not source for source in normalized):
            raise ValueError("source names must not be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("source names must be unique")
        object.__setattr__(self, "ordered_sources", normalized)

    def rank(self, source: str) -> int | None:
        """Return zero-based rank, or None when the source is unknown."""
        try:
            return self.ordered_sources.index(source)
        except ValueError:
            return None

    def prefers(self, candidate: str, incumbent: str) -> bool:
        """Return whether candidate outranks incumbent under this injected order."""
        candidate_rank = self.rank(candidate)
        incumbent_rank = self.rank(incumbent)
        if candidate_rank is None:
            return False
        if incumbent_rank is None:
            return True
        return candidate_rank < incumbent_rank
