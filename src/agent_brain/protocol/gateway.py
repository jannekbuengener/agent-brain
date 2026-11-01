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
from agent_brain.protocol.operations import dispatch_operation, operation_context_read
from agent_brain.protocol.runtime import ProtocolRuntime, default_runtime


class ProtocolGateway:
    """Thin application facade over existing Agent Brain core packages."""

    def __init__(self, runtime: ProtocolRuntime | None = None) -> None:
        self._runtime = runtime if runtime is not None else default_runtime()

    @property
    def runtime(self) -> ProtocolRuntime:
        return self._runtime

    def _prepare(
        self, request: ProtocolRequest | Mapping[str, Any],
    ) -> ProtocolRequest | ProtocolResponse:
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
        return request

    @staticmethod
    def _success(request: ProtocolRequest, data: Mapping[str, Any]) -> ProtocolResponse:
        return success_response(
            request.operation,
            redact_sensitive_mapping(dict(data)),
            limitations=tuple(str(item) for item in (data.get("limitations") or ())),
            request_id=request.request_id,
        )

    @staticmethod
    def _failure(request: ProtocolRequest, exc: Exception) -> ProtocolResponse:
        error = (
            ProtocolError(
                exc.code, exc.message,
                details=redact_sensitive_mapping(dict(exc.details or {})),
            )
            if isinstance(exc, ProtocolError)
            else ProtocolError(
                ProtocolErrorCode.INTERNAL_FAILURE,
                "internal protocol failure",
                details={"exception_type": type(exc).__name__},
            )
        )
        return failure_response(request.operation, error, request_id=request.request_id)

    async def invoke(self, request: ProtocolRequest | Mapping[str, Any]) -> ProtocolResponse:
        prepared = self._prepare(request)
        if isinstance(prepared, ProtocolResponse):
            return prepared
        try:
            data = await dispatch_operation(prepared.operation, prepared.payload, self._runtime)
            return self._success(prepared, data)
        except Exception as exc:  # noqa: BLE001 - never leak stack to consumers
            return self._failure(prepared, exc)

    def invoke_sync(self, request: ProtocolRequest | Mapping[str, Any]) -> ProtocolResponse:
        prepared = self._prepare(request)
        if isinstance(prepared, ProtocolResponse):
            return prepared
        if prepared.operation != "context_read":
            return asyncio.run(self.invoke(prepared))
        # context_read is a pure synchronous builder, with no backend I/O.
        # Starting an event loop here creates a Windows socketpair self-pipe
        # that can block in accept() in restricted stdio hosts before any work.
        try:
            return self._success(
                prepared, operation_context_read(prepared.payload, self._runtime),
            )
        except Exception as exc:  # noqa: BLE001 - same boundary as async invoke
            return self._failure(prepared, exc)


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
