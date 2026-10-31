"""Typed, fail-closed MemoryScope (#39).

Backend permissions/grants are intentionally out of scope. This contract only
describes visibility/ownership for read queries. Invalid or incomplete scope
information fails closed — it never silently widens to a broader region.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from agent_brain.contracts.versioning import require_compatible_version
from agent_brain.memory.errors import InvalidMemoryScope

MEMORY_SCOPE_SCHEMA = "memory-scope/v1"


class MemoryScopeKind(StrEnum):
    """Explicit scope kinds. Absence of a kind is never treated as global."""

    GLOBAL = "global"
    TENANT = "tenant"
    AGENT = "agent"
    SESSION = "session"
    SUBJECT = "subject"


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise InvalidMemoryScope(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise InvalidMemoryScope(f"{field_name} must not be blank")
    return normalized


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field_name)


@dataclass(frozen=True, slots=True)
class MemoryScope:
    """Locally validated visibility/ownership scope for memory reads.

    Construction validates kind-specific required identity fields. Extra
    identity fields that do not belong to the declared kind are rejected so
    callers cannot accidentally smuggle a narrower or wider intent.
    """

    schema_version: str
    kind: MemoryScopeKind
    tenant_id: str | None = None
    agent_id: str | None = None
    session_id: str | None = None
    subject_ref: str | None = None

    def __post_init__(self) -> None:
        try:
            require_compatible_version(
                self.schema_version,
                expected_family="memory-scope",
                supported_major=1,
            )
        except (TypeError, ValueError) as exc:
            raise InvalidMemoryScope(str(exc)) from exc

        kind = self.kind
        if isinstance(kind, str) and not isinstance(kind, MemoryScopeKind):
            try:
                kind = MemoryScopeKind(kind.strip())
            except ValueError as exc:
                raise InvalidMemoryScope(
                    f"kind must be one of {[member.value for member in MemoryScopeKind]}"
                ) from exc
            object.__setattr__(self, "kind", kind)
        if not isinstance(self.kind, MemoryScopeKind):
            raise InvalidMemoryScope("kind must be a MemoryScopeKind")

        tenant_id = _optional_text(self.tenant_id, "tenant_id")
        agent_id = _optional_text(self.agent_id, "agent_id")
        session_id = _optional_text(self.session_id, "session_id")
        subject_ref = _optional_text(self.subject_ref, "subject_ref")
        object.__setattr__(self, "tenant_id", tenant_id)
        object.__setattr__(self, "agent_id", agent_id)
        object.__setattr__(self, "session_id", session_id)
        object.__setattr__(self, "subject_ref", subject_ref)

        self._validate_shape()

    def _validate_shape(self) -> None:
        kind = self.kind
        if kind is MemoryScopeKind.GLOBAL:
            if any(
                value is not None
                for value in (
                    self.tenant_id,
                    self.agent_id,
                    self.session_id,
                    self.subject_ref,
                )
            ):
                raise InvalidMemoryScope(
                    "global scope must not carry tenant_id/agent_id/session_id/subject_ref"
                )
            return

        if kind is MemoryScopeKind.TENANT:
            if self.tenant_id is None:
                raise InvalidMemoryScope("tenant scope requires tenant_id")
            if any(
                value is not None
                for value in (self.agent_id, self.session_id, self.subject_ref)
            ):
                raise InvalidMemoryScope(
                    "tenant scope must not carry agent_id/session_id/subject_ref"
                )
            return

        if kind is MemoryScopeKind.AGENT:
            if self.tenant_id is None or self.agent_id is None:
                raise InvalidMemoryScope("agent scope requires tenant_id and agent_id")
            if any(value is not None for value in (self.session_id, self.subject_ref)):
                raise InvalidMemoryScope(
                    "agent scope must not carry session_id/subject_ref"
                )
            return

        if kind is MemoryScopeKind.SESSION:
            if (
                self.tenant_id is None
                or self.agent_id is None
                or self.session_id is None
            ):
                raise InvalidMemoryScope(
                    "session scope requires tenant_id, agent_id, and session_id"
                )
            if self.subject_ref is not None:
                raise InvalidMemoryScope("session scope must not carry subject_ref")
            return

        if kind is MemoryScopeKind.SUBJECT:
            if self.subject_ref is None:
                raise InvalidMemoryScope("subject scope requires subject_ref")
            if any(
                value is not None
                for value in (self.tenant_id, self.agent_id, self.session_id)
            ):
                raise InvalidMemoryScope(
                    "subject scope must not carry tenant_id/agent_id/session_id"
                )
            return

        raise InvalidMemoryScope(f"unsupported scope kind: {kind!r}")

    def matches(self, other: MemoryScope) -> bool:
        """Exact scope equality for isolation checks (no hierarchical fallback)."""
        if not isinstance(other, MemoryScope):
            raise InvalidMemoryScope("other must be a MemoryScope")
        return self == other

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "kind": self.kind.value,
        }
        for field_name in ("tenant_id", "agent_id", "session_id", "subject_ref"):
            value = getattr(self, field_name)
            if value is not None:
                payload[field_name] = value
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> MemoryScope:
        if not isinstance(payload, Mapping):
            raise InvalidMemoryScope("MemoryScope payload must be a mapping")
        kind_raw = payload.get("kind")
        if kind_raw is None:
            raise InvalidMemoryScope("kind is required; missing kind is not global")
        return cls(
            schema_version=str(payload.get("schema_version", "")),
            kind=kind_raw,  # type: ignore[arg-type]
            tenant_id=payload.get("tenant_id"),
            agent_id=payload.get("agent_id"),
            session_id=payload.get("session_id"),
            subject_ref=payload.get("subject_ref"),
        )

    @classmethod
    def global_scope(cls) -> MemoryScope:
        """Explicit typed global region — never implied by missing fields."""
        return cls(schema_version=MEMORY_SCOPE_SCHEMA, kind=MemoryScopeKind.GLOBAL)
