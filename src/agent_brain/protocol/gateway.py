"""Application gateway: single entry for CLI / MCP / future consumers."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from agent_brain.core.redaction import redact_sensitive_mapping
from agent_brain.protocol.errors import ProtocolError, ProtocolErrorCode
from agent_brain.protocol.models import (
    FORBIDDEN_WRITE_OPERATIONS,
    PUBLIC_OPERATIONS,
    ProtocolRequest,
    ProtocolResponse,
    failure_response,
    success_response,
)
from agent_brain.protocol.operations import dispatch_operation
from agent_brain.protocol.runtime import ProtocolRuntime, default_runtime


class ProtocolGateway:
    """Thin application facade over existing Agent Brain core packages."""

    def __init__(self, runtime: ProtocolRuntime | None = None) -> None:
        self._runtime = runtime if runtime is not None else default_runtime()

    @property
    def runtime(self) -> ProtocolRuntime:
        return self._runtime

    async def invoke(self, request: ProtocolRequest | Mapping[str, Any]) -> ProtocolResponse:
        if isinstance(request, Mapping):
            try:
                request = ProtocolRequest(
                    operation=str(request.get("operation", "")),
                    payload=dict(request.get("payload") or {}),
                    request_id=request.get("request_id"),  # type: ignore[arg-type]
                )
            except ProtocolError as exc:
                return failure_response("invalid", exc)

        operation = request.operation
        if operation in FORBIDDEN_WRITE_OPERATIONS:
            return failure_response(
                operation,
                ProtocolError(
                    ProtocolErrorCode.UNSUPPORTED_OPERATION,
                    f"write operation rejected by read-only boundary: {operation}",
                    details={"operation": operation, "read_only": True},
                ),
                request_id=request.request_id,
                limitations=("read_only_boundary",),
            )
        if operation not in PUBLIC_OPERATIONS:
            return failure_response(
                operation,
                ProtocolError(
                    ProtocolErrorCode.UNSUPPORTED_OPERATION,
                    f"unsupported operation: {operation}",
                    details={"operation": operation},
                ),
                request_id=request.request_id,
            )

        try:
            data = await dispatch_operation(operation, request.payload, self._runtime)
            limitations = tuple(str(item) for item in (data.get("limitations") or ()))
            # Keep response data free of nested limitations duplication when present
            # as a top-level health/capability field — still include on envelope.
            return success_response(
                operation,
                redact_sensitive_mapping(data),
                limitations=limitations,
                request_id=request.request_id,
            )
        except ProtocolError as exc:
            return failure_response(
                operation,
                ProtocolError(
                    exc.code,
                    exc.message,
                    details=redact_sensitive_mapping(dict(exc.details or {})),
                ),
                request_id=request.request_id,
            )
        except Exception as exc:  # noqa: BLE001 - never leak stack to consumers
            return failure_response(
                operation,
                ProtocolError(
                    ProtocolErrorCode.INTERNAL_FAILURE,
                    "internal protocol failure",
                    details={"exception_type": type(exc).__name__},
                ),
                request_id=request.request_id,
            )

    def invoke_sync(self, request: ProtocolRequest | Mapping[str, Any]) -> ProtocolResponse:
        return asyncio.run(self.invoke(request))


def invoke(
    operation: str,
    payload: Mapping[str, Any] | None = None,
    *,
    runtime: ProtocolRuntime | None = None,
    request_id: str | None = None,
) -> ProtocolResponse:
    """Sync convenience used by CLI and consumer fixtures."""
    gateway = ProtocolGateway(runtime=runtime)
    return gateway.invoke_sync(
        ProtocolRequest(
            operation=operation,
            payload=dict(payload or {}),
            request_id=request_id,
        )
    )


__all__ = [
    "ProtocolGateway",
    "invoke",
]
