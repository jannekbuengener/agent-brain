"""State-handoff decision gate for #21 consuming #38 inventory facts.

``STATE_HANDOFF_GO`` requires either migrated primary state or demonstrably
absent/empty primary classes on an owner-confirmed SurrealDB primary volume.
``UNAVAILABLE`` class status or unconfirmed volume authority yields
``STATE_HANDOFF_BLOCKED`` — never a silent empty interpretation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from agent_brain.surrealdb.state_classification import (
    CANONICAL_STATE_CLASSES,
    StateClassFinding,
    StateClassStatus,
    issue_38_scratch_findings_2026_10_31,
)


class HandoffOutcome(StrEnum):
    STATE_HANDOFF_GO = "STATE_HANDOFF_GO"
    STATE_HANDOFF_BLOCKED = "STATE_HANDOFF_BLOCKED"


class VolumeAuthority(StrEnum):
    """Whether the inventoried volume is accepted as Agent-Brain primary."""

    CONFIRMED_PRIMARY = "confirmed_primary"
    UNCONFIRMED = "unconfirmed"
    ELSEWHERE = "elsewhere"
    NEVER_CREATED = "never_created"


class StateDisposition(StrEnum):
    MIGRATE = "MIGRATE"
    REBUILD_FROM_SOURCE = "REBUILD_FROM_SOURCE"
    DROP_WITH_REASON = "DROP_WITH_REASON"
    DEFER = "DEFER"
    NOOP_ABSENT = "NOOP_ABSENT"


@dataclass(frozen=True, slots=True)
class ClassDisposition:
    state_class: str
    status: StateClassStatus
    disposition: StateDisposition
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class StateHandoffDecision:
    outcome: HandoffOutcome
    evidence_ref: str
    volume_authority: VolumeAuthority
    class_dispositions: tuple[ClassDisposition, ...]
    blocker_reason: str | None = None

    @property
    def is_go(self) -> bool:
        return self.outcome is HandoffOutcome.STATE_HANDOFF_GO


def _disposition_for_absent(state_class: str) -> StateDisposition:
    # Reconstructible knowledge mirrors stay rebuild; memory/evidence primary
    # classes that are absent need no migrate.
    if state_class in {"evidence", "evidence_ref", "claim", "audit_observation"}:
        return StateDisposition.NOOP_ABSENT
    if state_class in {"agent_memory", "shared_memory"}:
        return StateDisposition.NOOP_ABSENT
    return StateDisposition.DEFER


def decide_state_handoff(
    findings: tuple[StateClassFinding, ...] | list[StateClassFinding],
    *,
    volume_authority: VolumeAuthority,
    evidence_ref: str,
) -> StateHandoffDecision:
    """Derive GO/BLOCKED from classified findings + volume authority."""
    if not evidence_ref.strip():
        raise ValueError("evidence_ref must not be blank")
    if not isinstance(volume_authority, VolumeAuthority):
        volume_authority = VolumeAuthority(volume_authority)

    by_name = {item.state_class: item for item in findings}
    missing = [name for name in CANONICAL_STATE_CLASSES if name not in by_name]
    if missing:
        return StateHandoffDecision(
            outcome=HandoffOutcome.STATE_HANDOFF_BLOCKED,
            evidence_ref=evidence_ref,
            volume_authority=volume_authority,
            class_dispositions=(),
            blocker_reason=f"incomplete findings; missing classes: {missing}",
        )

    unavailable = [
        item.state_class
        for item in findings
        if item.status is StateClassStatus.UNAVAILABLE
    ]
    if unavailable:
        return StateHandoffDecision(
            outcome=HandoffOutcome.STATE_HANDOFF_BLOCKED,
            evidence_ref=evidence_ref,
            volume_authority=volume_authority,
            class_dispositions=tuple(
                ClassDisposition(
                    state_class=item.state_class,
                    status=item.status,
                    disposition=StateDisposition.DEFER,
                    detail=item.detail,
                )
                for item in findings
            ),
            blocker_reason=(
                "one or more state classes remain UNAVAILABLE: "
                + ", ".join(unavailable)
            ),
        )

    if volume_authority is VolumeAuthority.UNCONFIRMED:
        return StateHandoffDecision(
            outcome=HandoffOutcome.STATE_HANDOFF_BLOCKED,
            evidence_ref=evidence_ref,
            volume_authority=volume_authority,
            class_dispositions=tuple(
                ClassDisposition(
                    state_class=item.state_class,
                    status=item.status,
                    disposition=StateDisposition.DEFER,
                    detail=item.detail,
                )
                for item in findings
            ),
            blocker_reason=(
                "volume authority unconfirmed; owner must confirm the inventoried "
                "SurrealDB volume is Agent-Brain primary, ELSEWHERE, or NEVER_CREATED"
            ),
        )

    if volume_authority is VolumeAuthority.ELSEWHERE:
        return StateHandoffDecision(
            outcome=HandoffOutcome.STATE_HANDOFF_BLOCKED,
            evidence_ref=evidence_ref,
            volume_authority=volume_authority,
            class_dispositions=tuple(
                ClassDisposition(
                    state_class=item.state_class,
                    status=item.status,
                    disposition=StateDisposition.DEFER,
                    detail=item.detail,
                )
                for item in findings
            ),
            blocker_reason="primary SurrealDB state is declared ELSEWHERE; inventarize that store",
        )

    # CONFIRMED_PRIMARY or NEVER_CREATED with no UNAVAILABLE findings.
    present = [
        item for item in findings if item.status is StateClassStatus.PRESENT
    ]
    if present:
        return StateHandoffDecision(
            outcome=HandoffOutcome.STATE_HANDOFF_BLOCKED,
            evidence_ref=evidence_ref,
            volume_authority=volume_authority,
            class_dispositions=tuple(
                ClassDisposition(
                    state_class=item.state_class,
                    status=item.status,
                    disposition=(
                        StateDisposition.MIGRATE
                        if item.status is StateClassStatus.PRESENT
                        else _disposition_for_absent(item.state_class)
                    ),
                    detail=item.detail,
                )
                for item in findings
            ),
            blocker_reason=(
                "present primary classes require migrate proof before STATE_HANDOFF_GO: "
                + ", ".join(item.state_class for item in present)
            ),
        )

    dispositions = tuple(
        ClassDisposition(
            state_class=item.state_class,
            status=item.status,
            disposition=_disposition_for_absent(item.state_class),
            detail=item.detail,
        )
        for item in findings
    )
    return StateHandoffDecision(
        outcome=HandoffOutcome.STATE_HANDOFF_GO,
        evidence_ref=evidence_ref,
        volume_authority=volume_authority,
        class_dispositions=dispositions,
        blocker_reason=None,
    )


def issue_38_scratch_handoff_decision_2026_10_31(
    *,
    volume_authority: VolumeAuthority = VolumeAuthority.UNCONFIRMED,
) -> StateHandoffDecision:
    """Live #38 scratch gate input; default authority remains unconfirmed."""
    return decide_state_handoff(
        issue_38_scratch_findings_2026_10_31(),
        volume_authority=volume_authority,
        evidence_ref="docs/surrealdb/RUNTIME_BASELINE_2026-10-31.md",
    )
