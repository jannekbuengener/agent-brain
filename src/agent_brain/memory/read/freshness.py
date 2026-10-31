"""Derive CURRENT / STALE / SUPERSEDED / UNKNOWN for Memory entries (#11).

Consumes #37 ``TemporalEnvelope`` / ``ResolutionMeta`` / ``ResolutionState``
unchanged. No second temporal or supersession semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from agent_brain.contracts.resolution import ResolutionState
from agent_brain.contracts.temporal import TemporalEnvelope
from agent_brain.memory.read.models import MemoryEntry

# Higher precedence wins when multiple reasons apply (UNKNOWN > SUPERSEDED > STALE).
_STATE_PRECEDENCE = {
    ResolutionState.UNKNOWN: 3,
    ResolutionState.SUPERSEDED: 2,
    ResolutionState.STALE: 1,
    ResolutionState.CURRENT: 0,
}


@dataclass(frozen=True, slots=True)
class FreshnessDerivation:
    """Derived read-side state plus machine-readable reason codes."""

    resolution_state: ResolutionState
    reason_codes: tuple[str, ...]
    explanation: str


def _normalize_as_of(as_of: datetime) -> datetime:
    if not isinstance(as_of, datetime):
        raise TypeError("as_of must be a datetime")
    if as_of.tzinfo is None:
        return as_of
    from datetime import UTC

    return as_of.astimezone(UTC).replace(tzinfo=None)


def _pick(
    candidates: list[tuple[ResolutionState, str, str]],
) -> FreshnessDerivation:
    if not candidates:
        return FreshnessDerivation(
            resolution_state=ResolutionState.CURRENT,
            reason_codes=("current",),
            explanation="Within temporal bounds and not superseded.",
        )
    best_state = max(candidates, key=lambda item: _STATE_PRECEDENCE[item[0]])[0]
    selected = [item for item in candidates if item[0] is best_state]
    reasons = tuple(item[1] for item in selected)
    explanation = "; ".join(item[2] for item in selected)
    return FreshnessDerivation(
        resolution_state=best_state,
        reason_codes=reasons,
        explanation=explanation,
    )


def derive_memory_resolution_state(
    entry: MemoryEntry,
    *,
    as_of: datetime,
    known_supersession_targets: frozenset[str] | set[str] | None = None,
) -> FreshnessDerivation:
    """Derive ResolutionState from temporal, TTL, and supersession metadata.

    Rules (fail-closed, no silent positive defaults):
    - known_at > as_of → UNKNOWN (not yet known)
    - valid_from > as_of → UNKNOWN (not yet valid)
    - valid_until <= as_of → STALE
    - ttl_seconds elapsed from known_at → STALE (exact boundary: as_of >= expiry)
    - superseded_by_ref set and target known → SUPERSEDED
    - superseded_by_ref set and target unknown → UNKNOWN (broken chain)
    - contradictory known/valid ordering already rejected by TemporalEnvelope
    """
    if not isinstance(entry, MemoryEntry):
        raise TypeError("entry must be a MemoryEntry")
    ref = _normalize_as_of(as_of)
    temporal: TemporalEnvelope = entry.temporal
    meta = entry.resolution_meta
    known_ids = set(known_supersession_targets or ())
    candidates: list[tuple[ResolutionState, str, str]] = []

    if temporal.known_at > ref:
        candidates.append(
            (
                ResolutionState.UNKNOWN,
                "not_yet_known",
                "known_at is after as_of",
            )
        )
    if temporal.valid_from is not None and temporal.valid_from > ref:
        candidates.append(
            (
                ResolutionState.UNKNOWN,
                "not_yet_valid",
                "valid_from is after as_of",
            )
        )
    if temporal.valid_until is not None and temporal.valid_until <= ref:
        candidates.append(
            (
                ResolutionState.STALE,
                "validity_window_closed",
                "valid_until is at or before as_of",
            )
        )

    if entry.ttl_seconds is not None and entry.ttl_seconds > 0:
        expires_at = temporal.known_at + timedelta(seconds=entry.ttl_seconds)
        if ref >= expires_at:
            candidates.append(
                (
                    ResolutionState.STALE,
                    "ttl_elapsed",
                    f"ttl_seconds={entry.ttl_seconds} elapsed at as_of",
                )
            )

    target = meta.superseded_by_ref
    if target:
        if target in known_ids:
            candidates.append(
                (
                    ResolutionState.SUPERSEDED,
                    "superseded_by_ref",
                    f"Superseded by {target}",
                )
            )
        else:
            candidates.append(
                (
                    ResolutionState.UNKNOWN,
                    "broken_supersession_chain",
                    "superseded_by_ref target is unknown",
                )
            )

    return _pick(candidates)


__all__ = [
    "FreshnessDerivation",
    "derive_memory_resolution_state",
]
