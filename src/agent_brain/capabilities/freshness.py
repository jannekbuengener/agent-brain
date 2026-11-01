"""Live-revalidation / freshness semantics for capability responses.

Reuses canonical Agent Brain states instead of inventing a second taxonomy:

- ``ResolutionState``: CURRENT / STALE / SUPERSEDED / UNKNOWN
- ``LiveRevalidationStatus``: CONFIRMED / CONTRADICTED / UNAVAILABLE / NOT_APPLICABLE
- Response ``limitations`` may carry ``partial_source_state`` when some sources
  are missing while others remain usable (PARTIAL).

Hard invariants:
- UNAVAILABLE != EMPTY
- STALE != CURRENT
- NO_EVIDENCE != CONFIRMED
- Live / GitHub / Repo state outranks persisted context
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from agent_brain.contracts.resolution import ResolutionState
from agent_brain.core.source_priority import SourcePriority
from agent_brain.protocol.errors import ProtocolError, ProtocolErrorCode

# Semantic aliases documented for host adapters — not a competing enum set.
FRESHNESS_CURRENT = ResolutionState.CURRENT.value
FRESHNESS_STALE = ResolutionState.STALE.value
FRESHNESS_SUPERSEDED = ResolutionState.SUPERSEDED.value
FRESHNESS_UNKNOWN = ResolutionState.UNKNOWN.value
LIMITATION_PARTIAL = "partial_source_state"
LIMITATION_UNAVAILABLE = "source_unavailable"
LIMITATION_NO_EVIDENCE = "no_evidence"


@dataclass(frozen=True, slots=True)
class AuthoritativeSelection:
    """Outcome of preferring live state over stale persisted context."""

    payload: Mapping[str, Any]
    resolution_state: ResolutionState
    winning_source: str
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "payload": dict(self.payload),
            "resolution_state": self.resolution_state.value,
            "winning_source": self.winning_source,
            "limitations": list(self.limitations),
        }


def prefer_live_over_persisted(
    *,
    live_payload: Mapping[str, Any] | None,
    live_source: str,
    live_available: bool,
    persisted_payload: Mapping[str, Any] | None,
    persisted_source: str,
    persisted_state: ResolutionState,
    source_priority: SourcePriority,
    partial: bool = False,
) -> AuthoritativeSelection:
    """Select authoritative context under Agent Brain source priority.

    Live wins whenever available and preferred by ``source_priority``.
    Persisted stale context is never silently returned as CURRENT when live
    is available. Unavailable live checks never confirm persisted content.
    """
    limitations: list[str] = []
    if partial:
        limitations.append(LIMITATION_PARTIAL)

    if live_available and live_payload is not None:
        if not source_priority.prefers(live_source, persisted_source):
            # Live is available but does not outrank persisted — fail closed
            # rather than inventing a win for weaker sources.
            raise ProtocolError(
                ProtocolErrorCode.INTERNAL_FAILURE,
                "live source available but does not outrank persisted source",
                details={"live_source": live_source, "persisted_source": persisted_source},
            )
        return AuthoritativeSelection(
            payload=dict(live_payload),
            resolution_state=ResolutionState.CURRENT,
            winning_source=live_source,
            limitations=tuple(limitations),
        )

    limitations.append(LIMITATION_UNAVAILABLE)
    if persisted_payload is None:
        raise ProtocolError(
            ProtocolErrorCode.BACKEND_UNAVAILABLE,
            "live source unavailable and no persisted context present",
            details={
                "live_source": live_source,
                "persisted_source": persisted_source,
            },
        )

    # Live unavailable: surface persisted with its true state — never upgrade
    # STALE/UNKNOWN to CURRENT.
    state = persisted_state
    if state is ResolutionState.CURRENT:
        # Without live confirmation, do not claim CURRENT.
        state = ResolutionState.UNKNOWN
        limitations.append("live_unconfirmed")

    return AuthoritativeSelection(
        payload=dict(persisted_payload),
        resolution_state=state,
        winning_source=persisted_source,
        limitations=tuple(dict.fromkeys(limitations)),
    )


__all__ = [
    "FRESHNESS_CURRENT",
    "FRESHNESS_STALE",
    "FRESHNESS_SUPERSEDED",
    "FRESHNESS_UNKNOWN",
    "LIMITATION_NO_EVIDENCE",
    "LIMITATION_PARTIAL",
    "LIMITATION_UNAVAILABLE",
    "AuthoritativeSelection",
    "prefer_live_over_persisted",
]
