"""Observation-writer port — no management or Memory/Knowledge mutation surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agent_brain.contracts.improvement import (
    Improvement,
    ImprovementLifecycle,
    ImprovementObservation,
)


@dataclass(frozen=True, slots=True)
class SubmitObservationResult:
    """Result of an idempotent observation submit."""

    observation: ImprovementObservation
    improvement: Improvement
    created_new_observation: bool
    created_new_improvement: bool


class ImprovementObservationStore(Protocol):
    """Append-only Observation write + Improvement read boundary.

    Observation writers may submit evidence and read derived Improvements.
    They must not gain priority/lifecycle/merge/work-item mutation authority
    through this port — that belongs to ``ImprovementManagementPort`` (#52).
    """

    def submit_observation(self, observation: ImprovementObservation) -> SubmitObservationResult:
        """Append an observation idempotently and refresh derived aggregate fields."""

    def get_improvement(self, improvement_id: str) -> Improvement | None:
        """Return one Improvement aggregate, or None when unknown."""

    def list_improvements(
        self,
        *,
        skill_id: str | None = None,
        repository_ref: str | None = None,
        lifecycle: ImprovementLifecycle | str | None = None,
    ) -> tuple[Improvement, ...]:
        """List Improvements filtered by optional skill/repo/lifecycle."""

    def list_observations(self, improvement_id: str) -> tuple[ImprovementObservation, ...]:
        """Return append-only Observation history for one Improvement."""

    def find_candidates(
        self,
        *,
        skill_id: str,
        root_cause_key: str | None = None,
        repository_ref: str | None = None,
    ) -> tuple[Improvement, ...]:
        """Return exact-identity or scoped candidates; never auto-merge."""
