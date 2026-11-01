"""Versioned host-neutral Capability Contract identity (#73 Goal 1).

Contract identity is distinct from the #17 package version, but is always
bound to it — never a competing package truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent_brain import __version__ as package_version
from agent_brain.capabilities.names import (
    CAPABILITY_NAME,
    PRODUCT_NAME,
    REQUIRED_CAPABILITY_NAMES,
)
from agent_brain.distribution.version import PACKAGE_NAME, version_git_tag
from agent_brain.protocol.errors import ProtocolError, ProtocolErrorCode
from agent_brain.protocol.models import PROTOCOL_SCHEMA

# Explicit capability-contract identity. Major compatibility is the trailing /vN.
CAPABILITY_CONTRACT_SCHEMA = "agent-brain-cdb-context-capability/v1"
CAPABILITY_CONTRACT_MAJOR = 1
SUPPORTED_CONTRACT_SCHEMAS = frozenset({CAPABILITY_CONTRACT_SCHEMA})


@dataclass(frozen=True, slots=True)
class CapabilityContract:
    """Machine-readable identity for the host-neutral cdb_context surface."""

    product_name: str
    capability_name: str
    contract_schema: str
    contract_major: int
    agent_brain_version: str
    package_name: str
    protocol_schema: str
    required_capabilities: frozenset[str]
    read_only: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "product_name": self.product_name,
            "capability_name": self.capability_name,
            "contract_schema": self.contract_schema,
            "contract_major": self.contract_major,
            "agent_brain_version": self.agent_brain_version,
            "package_name": self.package_name,
            "git_tag": version_git_tag(self.agent_brain_version)
            if self.agent_brain_version != "0.0.0"
            else None,
            "protocol_schema": self.protocol_schema,
            "required_capabilities": sorted(self.required_capabilities),
            "read_only": self.read_only,
        }


def current_capability_contract() -> CapabilityContract:
    """Return the current contract bound to the #17 package version."""
    return CapabilityContract(
        product_name=PRODUCT_NAME,
        capability_name=CAPABILITY_NAME,
        contract_schema=CAPABILITY_CONTRACT_SCHEMA,
        contract_major=CAPABILITY_CONTRACT_MAJOR,
        agent_brain_version=package_version,
        package_name=PACKAGE_NAME,
        protocol_schema=PROTOCOL_SCHEMA,
        required_capabilities=REQUIRED_CAPABILITY_NAMES,
        read_only=True,
    )


def normalize_requested_contract_version(raw: object | None) -> str | None:
    """Normalize an optional caller-supplied contract version.

    Accepts the full schema string or a bare major like ``\"1\"`` / ``1``.
    ``None`` / blank means \"use current\".
    """
    if raw is None:
        return None
    if isinstance(raw, int):
        return str(raw)
    if not isinstance(raw, str):
        raise ProtocolError(
            ProtocolErrorCode.INVALID_INPUT,
            "contract_version must be a string or integer when provided",
        )
    text = raw.strip()
    if not text:
        return None
    return text


def assert_compatible_contract_version(raw: object | None) -> str:
    """Fail closed on incompatible contract versions; no silent downgrade."""
    requested = normalize_requested_contract_version(raw)
    if requested is None:
        return CAPABILITY_CONTRACT_SCHEMA
    if requested in SUPPORTED_CONTRACT_SCHEMAS:
        return requested
    if requested == str(CAPABILITY_CONTRACT_MAJOR) or requested == f"v{CAPABILITY_CONTRACT_MAJOR}":
        return CAPABILITY_CONTRACT_SCHEMA
    raise ProtocolError(
        ProtocolErrorCode.CONTRACT_VERSION_MISMATCH,
        f"unsupported cdb_context capability contract version: {requested}",
        details={
            "requested": requested,
            "supported": sorted(SUPPORTED_CONTRACT_SCHEMAS),
            "supported_major": CAPABILITY_CONTRACT_MAJOR,
        },
    )


def contract_metadata(*, requested_version: object | None = None) -> dict[str, Any]:
    """Envelope metadata for capability responses."""
    effective = assert_compatible_contract_version(requested_version)
    contract = current_capability_contract()
    payload = contract.to_dict()
    payload["effective_contract_schema"] = effective
    return payload


__all__ = [
    "CAPABILITY_CONTRACT_MAJOR",
    "CAPABILITY_CONTRACT_SCHEMA",
    "SUPPORTED_CONTRACT_SCHEMAS",
    "CapabilityContract",
    "assert_compatible_contract_version",
    "contract_metadata",
    "current_capability_contract",
    "normalize_requested_contract_version",
]
