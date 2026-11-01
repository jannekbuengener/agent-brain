"""Canonical mapping from host-facing capabilities to Agent Brain surfaces.

Each required capability maps to exactly one existing protocol operation or one
existing domain primitive. No duplicated business logic lives here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from agent_brain.capabilities.names import (
    AGENT_BRAIN_HEALTH,
    CDB_CONTEXT_BRIEFING,
    CDB_CONTEXT_EVIDENCE,
    CDB_CONTEXT_REQUIRED_READS,
    CDB_CONTEXT_SEARCH,
    OPTIONAL_CAPABILITY_NAMES,
    REQUIRED_CAPABILITY_NAMES,
)
from agent_brain.protocol.errors import ProtocolError, ProtocolErrorCode


class BackendKind(StrEnum):
    """Where the capability is fulfilled."""

    PROTOCOL_OPERATION = "protocol_operation"
    DOMAIN_PRIMITIVE = "domain_primitive"


@dataclass(frozen=True, slots=True)
class CapabilityMapping:
    capability: str
    backend_kind: BackendKind
    protocol_operation: str | None
    domain_symbol: str
    description: str

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "capability": self.capability,
            "backend_kind": self.backend_kind.value,
            "domain_symbol": self.domain_symbol,
            "description": self.description,
        }
        if self.protocol_operation is not None:
            payload["protocol_operation"] = self.protocol_operation
        return payload


CAPABILITY_MAPPINGS: dict[str, CapabilityMapping] = {
    AGENT_BRAIN_HEALTH: CapabilityMapping(
        capability=AGENT_BRAIN_HEALTH,
        backend_kind=BackendKind.PROTOCOL_OPERATION,
        protocol_operation="health",
        domain_symbol="agent_brain.protocol.operations.operation_health",
        description="Agent Brain health / backend availability readback",
    ),
    CDB_CONTEXT_BRIEFING: CapabilityMapping(
        capability=CDB_CONTEXT_BRIEFING,
        backend_kind=BackendKind.PROTOCOL_OPERATION,
        protocol_operation="context_read",
        domain_symbol="agent_brain.context.build_briefing",
        description="CDB-profiled briefing via existing context_read / briefing contracts",
    ),
    CDB_CONTEXT_SEARCH: CapabilityMapping(
        capability=CDB_CONTEXT_SEARCH,
        backend_kind=BackendKind.PROTOCOL_OPERATION,
        protocol_operation="retrieval",
        domain_symbol="agent_brain.retrieval.run_retrieval",
        description="CDB-profiled search via existing hybrid retrieval contracts",
    ),
    CDB_CONTEXT_REQUIRED_READS: CapabilityMapping(
        capability=CDB_CONTEXT_REQUIRED_READS,
        backend_kind=BackendKind.DOMAIN_PRIMITIVE,
        protocol_operation=None,
        domain_symbol="agent_brain.context.resolve_required_reads",
        description="CDB RequiredReadsProfile resolved by existing product-neutral resolver",
    ),
    CDB_CONTEXT_EVIDENCE: CapabilityMapping(
        capability=CDB_CONTEXT_EVIDENCE,
        backend_kind=BackendKind.PROTOCOL_OPERATION,
        protocol_operation="evidence",
        domain_symbol="agent_brain.evidence.build_trust_summary",
        description="CDB evidence / trust via existing evidence surface",
    ),
}


def mapping_for(capability: str) -> CapabilityMapping:
    try:
        return CAPABILITY_MAPPINGS[capability]
    except KeyError as exc:
        if capability in OPTIONAL_CAPABILITY_NAMES:
            raise ProtocolError(
                ProtocolErrorCode.CAPABILITY_UNAVAILABLE,
                f"optional capability not exposed by current foundation: {capability}",
                details={"capability": capability, "optional": True},
            ) from exc
        raise ProtocolError(
            ProtocolErrorCode.CAPABILITY_UNAVAILABLE,
            f"unknown or unavailable capability: {capability}",
            details={"capability": capability},
        ) from exc


def assert_required_mappings_complete() -> None:
    missing = REQUIRED_CAPABILITY_NAMES - frozenset(CAPABILITY_MAPPINGS)
    if missing:
        raise RuntimeError(f"missing capability mappings: {sorted(missing)}")


assert_required_mappings_complete()


__all__ = [
    "CAPABILITY_MAPPINGS",
    "BackendKind",
    "CapabilityMapping",
    "assert_required_mappings_complete",
    "mapping_for",
]
