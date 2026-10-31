"""Live-State revalidation for Memory recall (#11).

Source priority remains: GitHub Live / Repo Live > verified evidence > Memory.
Memory never overwrites Live. Unavailable checks never confirm Memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from agent_brain.core.source_priority import SourcePriority
from agent_brain.memory.read.models import (
    LIVE_REVALIDATION_SCHEMA,
    LiveRevalidationResult,
    LiveRevalidationStatus,
    LiveStateClaim,
    MemoryEntry,
)

# Default authority order for injectable live sources. Callers may override.
DEFAULT_LIVE_SOURCE_PRIORITY = SourcePriority(
    ordered_sources=(
        "github_live",
        "repo_live",
        "verified_evidence",
        "memory",
    )
)


@dataclass(frozen=True, slots=True)
class LiveStateObservation:
    """One observation from an authoritative live checker."""

    claim_key: str
    value: str
    source: str
    available: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.claim_key, str) or not self.claim_key.strip():
            raise ValueError("claim_key must be a non-blank string")
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("value must be a non-blank string")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("source must be a non-blank string")
        if not isinstance(self.available, bool):
            raise TypeError("available must be a bool")
        object.__setattr__(self, "claim_key", self.claim_key.strip())
        object.__setattr__(self, "value", self.value.strip())
        object.__setattr__(self, "source", self.source.strip())


@runtime_checkable
class LiveStateChecker(Protocol):
    """Port for observing current live state for a claim key.

    Returning None means the checker could not answer (UNAVAILABLE), which must
    never be interpreted as confirmation of Memory.
    """

    def observe(self, claim_key: str) -> LiveStateObservation | None:
        """Return a live observation or None when the check is unavailable."""


@dataclass(frozen=True, slots=True)
class StaticLiveStateChecker:
    """Deterministic fixture checker for unit/contract tests."""

    observations: dict[str, LiveStateObservation | None]

    def observe(self, claim_key: str) -> LiveStateObservation | None:
        if claim_key not in self.observations:
            return None
        return self.observations[claim_key]


def revalidate_against_live_state(
    entry: MemoryEntry,
    *,
    checker: LiveStateChecker | None,
    source_priority: SourcePriority | None = None,
) -> LiveRevalidationResult:
    """Compare Memory live_claim against current live state.

    Outcomes:
    - no live_claim → NOT_APPLICABLE
    - checker is None / observe returns None / available=False → UNAVAILABLE
      (does not confirm Memory)
    - live value differs and live source outranks memory → CONTRADICTED
    - live value matches → CONFIRMED
    - live source does not outrank memory → UNAVAILABLE with
      insufficient_live_authority (fail-closed; Memory still does not win)
    """
    claim: LiveStateClaim | None = entry.live_claim
    if claim is None:
        return LiveRevalidationResult(
            schema_version=LIVE_REVALIDATION_SCHEMA,
            status=LiveRevalidationStatus.NOT_APPLICABLE,
            reason_code="no_live_claim",
        )

    if checker is None:
        return LiveRevalidationResult(
            schema_version=LIVE_REVALIDATION_SCHEMA,
            status=LiveRevalidationStatus.UNAVAILABLE,
            reason_code="live_checker_absent",
        )

    observation = checker.observe(claim.claim_key)
    if observation is None or not observation.available:
        return LiveRevalidationResult(
            schema_version=LIVE_REVALIDATION_SCHEMA,
            status=LiveRevalidationStatus.UNAVAILABLE,
            reason_code="live_check_unavailable",
            observed_source=None if observation is None else observation.source,
        )

    priority = source_priority or DEFAULT_LIVE_SOURCE_PRIORITY
    # Live must outrank Memory; otherwise we cannot treat the observation as
    # authoritative enough to confirm or safely contradict under this policy.
    if not priority.prefers(observation.source, "memory"):
        return LiveRevalidationResult(
            schema_version=LIVE_REVALIDATION_SCHEMA,
            status=LiveRevalidationStatus.UNAVAILABLE,
            observed_value=observation.value,
            observed_source=observation.source,
            reason_code="insufficient_live_authority",
        )

    if observation.value == claim.asserted_value:
        return LiveRevalidationResult(
            schema_version=LIVE_REVALIDATION_SCHEMA,
            status=LiveRevalidationStatus.CONFIRMED,
            observed_value=observation.value,
            observed_source=observation.source,
            reason_code="live_matches_memory",
        )

    return LiveRevalidationResult(
        schema_version=LIVE_REVALIDATION_SCHEMA,
        status=LiveRevalidationStatus.CONTRADICTED,
        observed_value=observation.value,
        observed_source=observation.source,
        reason_code="live_contradicts_memory",
    )


__all__ = [
    "DEFAULT_LIVE_SOURCE_PRIORITY",
    "LiveStateChecker",
    "LiveStateObservation",
    "StaticLiveStateChecker",
    "revalidate_against_live_state",
]
