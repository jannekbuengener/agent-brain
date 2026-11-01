"""Capability gateway: host-facing names → protocol / domain composition."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_brain.capabilities.cdb_context import (
    default_cdb_context_profile,
    invoke_briefing,
    invoke_evidence,
    invoke_required_reads,
    invoke_search,
)
from agent_brain.capabilities.contract import (
    CAPABILITY_CONTRACT_SCHEMA,
    assert_compatible_contract_version,
    contract_metadata,
)
from agent_brain.capabilities.mapping import mapping_for
from agent_brain.capabilities.names import (
    AGENT_BRAIN_HEALTH,
    CDB_CONTEXT_BRIEFING,
    CDB_CONTEXT_EVIDENCE,
    CDB_CONTEXT_REQUIRED_READS,
    CDB_CONTEXT_SEARCH,
)
from agent_brain.core.redaction import redact_sensitive_mapping
from agent_brain.protocol.errors import ProtocolError, ProtocolErrorCode
from agent_brain.protocol.gateway import ProtocolGateway
from agent_brain.protocol.models import (
    FORBIDDEN_WRITE_OPERATIONS,
    ProtocolRequest,
    ProtocolResponse,
    failure_response,
    success_response,
)
from agent_brain.protocol.runtime import ProtocolRuntime, default_runtime


class CapabilityGateway:
    """Thin facade over ProtocolGateway + CDB profile composers."""

    def __init__(
        self,
        runtime: ProtocolRuntime | None = None,
        *,
        protocol_gateway: ProtocolGateway | None = None,
    ) -> None:
        self._runtime = runtime if runtime is not None else default_runtime()
        self._protocol = (
            protocol_gateway
            if protocol_gateway is not None
            else ProtocolGateway(runtime=self._runtime)
        )
        self._profile = default_cdb_context_profile()

    @property
    def protocol(self) -> ProtocolGateway:
        return self._protocol

    def invoke(
        self,
        capability: str,
        payload: Mapping[str, Any] | None = None,
        *,
        contract_version: object | None = None,
        request_id: str | None = None,
    ) -> ProtocolResponse:
        data = dict(payload or {})
        # Allow contract_version inside payload or as explicit kwarg.
        if contract_version is None and "contract_version" in data:
            contract_version = data.pop("contract_version")

        try:
            if capability in FORBIDDEN_WRITE_OPERATIONS or capability.endswith(".write"):
                raise ProtocolError(
                    ProtocolErrorCode.UNSUPPORTED_OPERATION,
                    f"write operation rejected by read-only boundary: {capability}",
                    details={"capability": capability, "read_only": True},
                )

            effective_contract = assert_compatible_contract_version(contract_version)
            mapping = mapping_for(capability)

            if capability == AGENT_BRAIN_HEALTH:
                response = self._protocol.invoke_sync(
                    ProtocolRequest(operation="health", payload=data, request_id=request_id)
                )
            elif capability == CDB_CONTEXT_BRIEFING:
                response = invoke_briefing(
                    data, gateway=self._protocol, profile=self._profile
                )
            elif capability == CDB_CONTEXT_SEARCH:
                response = invoke_search(data, gateway=self._protocol, profile=self._profile)
            elif capability == CDB_CONTEXT_REQUIRED_READS:
                result = invoke_required_reads(data, profile=self._profile)
                response = success_response(
                    mapping.protocol_operation or "required_reads",
                    redact_sensitive_mapping(result),
                    request_id=request_id,
                )
            elif capability == CDB_CONTEXT_EVIDENCE:
                response = invoke_evidence(
                    data, gateway=self._protocol, profile=self._profile
                )
            else:
                raise ProtocolError(
                    ProtocolErrorCode.CAPABILITY_UNAVAILABLE,
                    f"capability unavailable: {capability}",
                    details={"capability": capability},
                )

            if not response.ok:
                assert response.error is not None
                return failure_response(
                    capability,
                    response.error,
                    limitations=response.limitations,
                    request_id=request_id or response.request_id,
                )

            envelope = dict(response.data or {})
            envelope["capability"] = capability
            envelope["capability_contract"] = contract_metadata(
                requested_version=effective_contract
            )
            envelope["mapping"] = mapping.to_dict()
            return ProtocolResponse(
                ok=True,
                operation=capability,
                agent_brain_version=response.agent_brain_version,
                protocol_schema=response.protocol_schema,
                data=redact_sensitive_mapping(envelope),
                limitations=response.limitations,
                request_id=request_id or response.request_id,
            )
        except ProtocolError as exc:
            return failure_response(
                capability or "invalid",
                ProtocolError(
                    exc.code,
                    exc.message,
                    details=redact_sensitive_mapping(dict(exc.details or {})),
                ),
                request_id=request_id,
                limitations=("read_only_boundary",)
                if exc.code is ProtocolErrorCode.UNSUPPORTED_OPERATION
                else (),
            )


def invoke_capability(
    capability: str,
    payload: Mapping[str, Any] | None = None,
    *,
    contract_version: object | None = None,
    request_id: str | None = None,
    runtime: ProtocolRuntime | None = None,
) -> ProtocolResponse:
    """Module-level convenience entry for host-neutral capability calls."""
    return CapabilityGateway(runtime=runtime).invoke(
        capability,
        payload,
        contract_version=contract_version,
        request_id=request_id,
    )


__all__ = [
    "CAPABILITY_CONTRACT_SCHEMA",
    "CapabilityGateway",
    "invoke_capability",
]
