"""Product-neutral policy hook contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol


def _required_operation(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("operation must not be blank")
    return normalized


@dataclass(frozen=True, slots=True)
class PolicyContext:
    """Operation and caller-supplied attributes presented to a policy hook."""

    operation: str
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation", _required_operation(self.operation))


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """Result returned by an injected policy hook."""

    allowed: bool
    reasons: tuple[str, ...] = ()


class PolicyHook(Protocol):
    """Interface for consumer-owned policy evaluation."""

    def evaluate(self, context: PolicyContext) -> PolicyDecision:
        """Evaluate one operation without granting domain authority to the core."""
