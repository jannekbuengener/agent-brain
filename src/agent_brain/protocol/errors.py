"""Structured protocol error semantics for the public #12 surface.

BACKEND_UNAVAILABLE must never be presented as an empty domain success.
INVALID_SCOPE must never be presented as NO_RESULTS.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ProtocolErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    INVALID_SCOPE = "invalid_scope"
    UNSUPPORTED_OPERATION = "unsupported_operation"
    CAPABILITY_UNAVAILABLE = "capability_unavailable"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    CONTRACT_VERSION_MISMATCH = "contract_version_mismatch"
    INTERNAL_FAILURE = "internal_failure"


# CLI / process exit codes for structured failures.
EXIT_SUCCESS = 0
EXIT_INTERNAL = 1
EXIT_INVALID = 2
EXIT_UNAVAILABLE = 3
EXIT_UNSUPPORTED = 4


def exit_code_for(code: ProtocolErrorCode) -> int:
    if code in {
        ProtocolErrorCode.INVALID_INPUT,
        ProtocolErrorCode.INVALID_SCOPE,
        ProtocolErrorCode.CONTRACT_VERSION_MISMATCH,
    }:
        return EXIT_INVALID
    if code in {
        ProtocolErrorCode.CAPABILITY_UNAVAILABLE,
        ProtocolErrorCode.BACKEND_UNAVAILABLE,
    }:
        return EXIT_UNAVAILABLE
    if code is ProtocolErrorCode.UNSUPPORTED_OPERATION:
        return EXIT_UNSUPPORTED
    return EXIT_INTERNAL


@dataclass(frozen=True, slots=True)
class ProtocolError(Exception):
    """Fail-closed protocol error with a stable machine-readable code."""

    code: ProtocolErrorCode
    message: str
    details: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, ProtocolErrorCode):
            object.__setattr__(self, "code", ProtocolErrorCode(self.code))
        msg = self.message.strip()
        if not msg:
            raise ValueError("message must not be blank")
        object.__setattr__(self, "message", msg)
        if self.details is None:
            object.__setattr__(self, "details", {})
        elif not isinstance(self.details, dict):
            raise TypeError("details must be a dict")

    def __str__(self) -> str:
        return f"{self.code.value}: {self.message}"

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code.value,
            "message": self.message,
            "details": dict(self.details or {}),
        }


__all__ = [
    "EXIT_INTERNAL",
    "EXIT_INVALID",
    "EXIT_SUCCESS",
    "EXIT_UNAVAILABLE",
    "EXIT_UNSUPPORTED",
    "ProtocolError",
    "ProtocolErrorCode",
    "exit_code_for",
]
