"""State-class classification helpers for #21 consuming #38 inventory facts.

These helpers never probe a live database. Callers pass already-verified
inventory outcomes so UNAVAILABLE cannot silently become ABSENT or EMPTY.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class StateClassStatus(StrEnum):
    """DB-backed status for a canonical #21 state class."""

    UNAVAILABLE = "unavailable"
    ABSENT = "absent"
    PRESENT = "present"


# Canonical #21 classes (issue text). Order is stable for reporting.
CANONICAL_STATE_CLASSES: tuple[str, ...] = (
    "agent_memory",
    "shared_memory",
    "evidence",
    "evidence_ref",
    "claim",
    "audit_observation",
)


@dataclass(frozen=True, slots=True)
class StateClassFinding:
    """One classified state class with explicit evidence provenance."""

    state_class: str
    status: StateClassStatus
    evidence_ref: str
    detail: str | None = None

    def __post_init__(self) -> None:
        name = self.state_class.strip()
        if not name:
            raise ValueError("state_class must not be blank")
        object.__setattr__(self, "state_class", name)
        if isinstance(self.status, str) and not isinstance(self.status, StateClassStatus):
            object.__setattr__(self, "status", StateClassStatus(self.status))
        if not isinstance(self.status, StateClassStatus):
            raise TypeError("status must be a StateClassStatus")
        ref = self.evidence_ref.strip()
        if not ref:
            raise ValueError("evidence_ref must not be blank")
        object.__setattr__(self, "evidence_ref", ref)


def classify_table_presence(
    *,
    table_exists: bool | None,
    evidence_ref: str,
    state_class: str,
) -> StateClassFinding:
    """Map table-existence evidence to UNAVAILABLE / ABSENT / PRESENT.

    ``table_exists is None`` means the backend could not answer (UNAVAILABLE).
    ``False`` is ABSENT. ``True`` is PRESENT (counts/fields remain separate).
    """
    if table_exists is None:
        status = StateClassStatus.UNAVAILABLE
        detail = "no DB-backed table-existence answer"
    elif table_exists:
        status = StateClassStatus.PRESENT
        detail = "table present"
    else:
        status = StateClassStatus.ABSENT
        detail = "table does not exist"
    return StateClassFinding(
        state_class=state_class,
        status=status,
        evidence_ref=evidence_ref,
        detail=detail,
    )


def classify_canonical_classes_from_table_map(
    table_presence: dict[str, bool | None],
    *,
    evidence_ref: str,
) -> tuple[StateClassFinding, ...]:
    """Classify all canonical #21 classes from an explicit presence map.

    Missing map keys are treated as UNAVAILABLE (not ABSENT).
    """
    findings: list[StateClassFinding] = []
    for name in CANONICAL_STATE_CLASSES:
        exists = table_presence.get(name)
        findings.append(
            classify_table_presence(
                table_exists=exists,
                evidence_ref=evidence_ref,
                state_class=name,
            )
        )
    return tuple(findings)


# Frozen #38 scratch inventory (2026-10-31): tables absent in checked DBs.
ISSUE_38_SCRATCH_TABLE_PRESENCE_2026_10_31: dict[str, bool | None] = {
    "agent_memory": False,
    "shared_memory": False,
    "evidence": False,
    "evidence_ref": False,
    "claim": False,
    "audit_observation": False,
}


def issue_38_scratch_findings_2026_10_31() -> tuple[StateClassFinding, ...]:
    """Return the verified #38 scratch classification for #21 consumption."""
    return classify_canonical_classes_from_table_map(
        ISSUE_38_SCRATCH_TABLE_PRESENCE_2026_10_31,
        evidence_ref="docs/surrealdb/RUNTIME_BASELINE_2026-10-31.md#21-state-classes",
    )
