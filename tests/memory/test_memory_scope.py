"""Fail-closed MemoryScope contract tests (#39)."""

from __future__ import annotations

import pytest

from agent_brain.memory import (
    MEMORY_SCOPE_SCHEMA,
    InvalidMemoryScope,
    MemoryScope,
    MemoryScopeKind,
)


def test_global_scope_is_explicit() -> None:
    scope = MemoryScope.global_scope()
    assert scope.kind is MemoryScopeKind.GLOBAL
    assert scope.to_dict() == {
        "schema_version": MEMORY_SCOPE_SCHEMA,
        "kind": "global",
    }


def test_missing_kind_is_not_global() -> None:
    with pytest.raises(InvalidMemoryScope, match="kind is required"):
        MemoryScope.from_dict({"schema_version": MEMORY_SCOPE_SCHEMA})


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        (
            {
                "schema_version": MEMORY_SCOPE_SCHEMA,
                "kind": "tenant",
            },
            "tenant scope requires tenant_id",
        ),
        (
            {
                "schema_version": MEMORY_SCOPE_SCHEMA,
                "kind": "agent",
                "tenant_id": "t1",
            },
            "agent scope requires tenant_id and agent_id",
        ),
        (
            {
                "schema_version": MEMORY_SCOPE_SCHEMA,
                "kind": "session",
                "tenant_id": "t1",
                "agent_id": "a1",
            },
            "session scope requires",
        ),
        (
            {
                "schema_version": MEMORY_SCOPE_SCHEMA,
                "kind": "subject",
            },
            "subject scope requires subject_ref",
        ),
        (
            {
                "schema_version": MEMORY_SCOPE_SCHEMA,
                "kind": "global",
                "tenant_id": "t1",
            },
            "global scope must not carry",
        ),
        (
            {
                "schema_version": MEMORY_SCOPE_SCHEMA,
                "kind": "tenant",
                "tenant_id": "t1",
                "agent_id": "a1",
            },
            "tenant scope must not carry",
        ),
        (
            {
                "schema_version": MEMORY_SCOPE_SCHEMA,
                "kind": "unknown",
            },
            "kind must be one of",
        ),
        (
            {
                "schema_version": MEMORY_SCOPE_SCHEMA,
                "kind": "tenant",
                "tenant_id": "   ",
            },
            "tenant_id must not be blank",
        ),
    ],
)
def test_invalid_scopes_fail_closed(payload: dict[str, object], match: str) -> None:
    with pytest.raises(InvalidMemoryScope, match=match):
        MemoryScope.from_dict(payload)


def test_valid_nested_scopes_roundtrip() -> None:
    session = MemoryScope(
        schema_version=MEMORY_SCOPE_SCHEMA,
        kind=MemoryScopeKind.SESSION,
        tenant_id="t1",
        agent_id="a1",
        session_id="s1",
    )
    restored = MemoryScope.from_dict(session.to_dict())
    assert restored == session
    assert restored.matches(session)


def test_scope_match_is_exact_not_hierarchical() -> None:
    tenant = MemoryScope(
        schema_version=MEMORY_SCOPE_SCHEMA,
        kind=MemoryScopeKind.TENANT,
        tenant_id="t1",
    )
    agent = MemoryScope(
        schema_version=MEMORY_SCOPE_SCHEMA,
        kind=MemoryScopeKind.AGENT,
        tenant_id="t1",
        agent_id="a1",
    )
    assert not tenant.matches(agent)
    assert not agent.matches(tenant)
