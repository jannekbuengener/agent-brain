"""Shared request/response DTOs for the public Application / Protocol Surface (#12).

Transport adapters (CLI, optional MCP) reuse these models. Domain logic stays in
existing core packages; this layer only shapes consumer contracts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from agent_brain import __version__ as package_version
from agent_brain.core.redaction import redact_sensitive_mapping
from agent_brain.distribution.version import PACKAGE_NAME, version_git_tag
from agent_brain.protocol.errors import ProtocolError, ProtocolErrorCode

PROTOCOL_SCHEMA = "agent-brain-protocol/v1"


class CapabilityId(StrEnum):
    """Public read-only capabilities. Only report when truly usable."""

    CONTEXT_READ = "context_read"
    RETRIEVAL = "retrieval"
    EVIDENCE = "evidence"
    MEMORY_READ = "memory_read"
    SURREAL_READ = "surreal_read"


class HealthState(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"


class CapabilityState(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


# Meta operations are always present on the surface (not domain capabilities).
META_OPERATIONS = frozenset({"version", "health", "capabilities"})
DOMAIN_OPERATIONS = frozenset(item.value for item in CapabilityId)
PUBLIC_OPERATIONS = META_OPERATIONS | DOMAIN_OPERATIONS

# Read-only boundary: these operation names must never be registered.
FORBIDDEN_WRITE_OPERATIONS = frozenset(
    {
        "write",
        "remember",
        "consolidate",
        "reflect",
        "seed",
        "repair",
        "mutate",
        "submit_improvement_observation",
        "merge_improvements",
        "set_improvement_priority",
        "transition_improvement_lifecycle",
        "link_work_item",
        "record_verification",
    }
)


def agent_brain_version_metadata() -> dict[str, object]:
    """Version metadata bound to the #17 package version source of truth."""
    return {
        "package_name": PACKAGE_NAME,
        "agent_brain_version": package_version,
        "git_tag": version_git_tag(package_version) if package_version != "0.0.0" else None,
        "protocol_schema": PROTOCOL_SCHEMA,
    }


@dataclass(frozen=True, slots=True)
class ProtocolRequest:
    """Transport-neutral request envelope."""

    operation: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    request_id: str | None = None

    def __post_init__(self) -> None:
        op = self.operation.strip() if isinstance(self.operation, str) else ""
        if not op:
            raise ProtocolError(
                ProtocolErrorCode.INVALID_INPUT,
                "operation must not be blank",
            )
        object.__setattr__(self, "operation", op)
        if self.payload is None:
            object.__setattr__(self, "payload", {})
        elif not isinstance(self.payload, Mapping):
            raise ProtocolError(
                ProtocolErrorCode.INVALID_INPUT,
                "payload must be a mapping",
            )
        else:
            object.__setattr__(self, "payload", dict(self.payload))
        if self.request_id is not None:
            rid = self.request_id.strip()
            if not rid:
                raise ProtocolError(
                    ProtocolErrorCode.INVALID_INPUT,
                    "request_id must not be blank when provided",
                )
            object.__setattr__(self, "request_id", rid)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "operation": self.operation,
            "payload": dict(self.payload),
        }
        if self.request_id is not None:
            payload["request_id"] = self.request_id
        return payload


@dataclass(frozen=True, slots=True)
class ComponentHealth:
    name: str
    state: HealthState
    detail: str | None = None

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"name": self.name, "state": self.state.value}
        if self.detail is not None:
            result["detail"] = self.detail
        return result


@dataclass(frozen=True, slots=True)
class HealthReport:
    schema_version: str
    overall: HealthState
    components: tuple[ComponentHealth, ...]
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "overall": self.overall.value,
            "components": [item.to_dict() for item in self.components],
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class CapabilityStatus:
    capability: CapabilityId
    state: CapabilityState
    detail: str | None = None

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "capability": self.capability.value,
            "state": self.state.value,
        }
        if self.detail is not None:
            result["detail"] = self.detail
        return result


@dataclass(frozen=True, slots=True)
class CapabilityReport:
    schema_version: str
    capabilities: tuple[CapabilityStatus, ...]
    read_only: bool = True

    def available_ids(self) -> frozenset[str]:
        return frozenset(
            item.capability.value
            for item in self.capabilities
            if item.state is CapabilityState.AVAILABLE
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "read_only": self.read_only,
            "capabilities": [item.to_dict() for item in self.capabilities],
        }


@dataclass(frozen=True, slots=True)
class ProtocolResponse:
    """Success or structured failure; never mixes UNAVAILABLE into empty data."""

    ok: bool
    operation: str
    agent_brain_version: str
    protocol_schema: str
    data: Mapping[str, Any] | None = None
    error: ProtocolError | None = None
    limitations: tuple[str, ...] = ()
    request_id: str | None = None

    def __post_init__(self) -> None:
        if self.ok:
            if self.error is not None:
                raise ValueError("successful response must not carry error")
            if self.data is None:
                object.__setattr__(self, "data", {})
        else:
            if self.error is None:
                raise ValueError("failed response requires error")
            object.__setattr__(self, "data", None)
        if self.data is not None and not isinstance(self.data, Mapping):
            raise TypeError("data must be a mapping")
        object.__setattr__(self, "limitations", tuple(self.limitations))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "ok": self.ok,
            "operation": self.operation,
            "agent_brain_version": self.agent_brain_version,
            "protocol_schema": self.protocol_schema,
            "limitations": list(self.limitations),
        }
        if self.request_id is not None:
            payload["request_id"] = self.request_id
        if self.ok:
            payload["data"] = redact_sensitive_mapping(dict(self.data or {}))
        else:
            assert self.error is not None
            payload["error"] = redact_sensitive_mapping(self.error.to_dict())
        return payload


def success_response(
    operation: str,
    data: Mapping[str, Any],
    *,
    limitations: Sequence[str] = (),
    request_id: str | None = None,
) -> ProtocolResponse:
    return ProtocolResponse(
        ok=True,
        operation=operation,
        agent_brain_version=package_version,
        protocol_schema=PROTOCOL_SCHEMA,
        data=dict(data),
        limitations=tuple(limitations),
        request_id=request_id,
    )


def failure_response(
    operation: str,
    error: ProtocolError,
    *,
    limitations: Sequence[str] = (),
    request_id: str | None = None,
) -> ProtocolResponse:
    return ProtocolResponse(
        ok=False,
        operation=operation,
        agent_brain_version=package_version,
        protocol_schema=PROTOCOL_SCHEMA,
        error=error,
        limitations=tuple(limitations),
        request_id=request_id,
    )


__all__ = [
    "DOMAIN_OPERATIONS",
    "FORBIDDEN_WRITE_OPERATIONS",
    "META_OPERATIONS",
    "PROTOCOL_SCHEMA",
    "PUBLIC_OPERATIONS",
    "CapabilityId",
    "CapabilityReport",
    "CapabilityState",
    "CapabilityStatus",
    "ComponentHealth",
    "HealthReport",
    "HealthState",
    "ProtocolRequest",
    "ProtocolResponse",
    "agent_brain_version_metadata",
    "failure_response",
    "success_response",
]
