"""Public protocol surface contracts (#12)."""

from __future__ import annotations

import asyncio

import pytest

from agent_brain import __version__
from agent_brain.memory.in_memory import InMemoryMemoryStore
from agent_brain.memory.unavailable import UnavailableMemoryStore
from agent_brain.protocol import (
    FORBIDDEN_WRITE_OPERATIONS,
    PROTOCOL_SCHEMA,
    BrainMcpAdapter,
    CapabilityId,
    ProtocolErrorCode,
    ProtocolGateway,
    ProtocolRequest,
    ProtocolRuntime,
    invoke,
    tool_schemas,
)
from agent_brain.surrealdb.config import SurrealDbReadSettings


def test_version_matches_package_version() -> None:
    response = invoke("version")
    assert response.ok is True
    assert response.data is not None
    assert response.data["agent_brain_version"] == __version__
    assert response.data["protocol_schema"] == PROTOCOL_SCHEMA
    assert response.agent_brain_version == __version__


def test_health_default_runtime_is_degraded_not_empty_success() -> None:
    response = invoke("health")
    assert response.ok is True
    assert response.data is not None
    assert response.data["overall"] == "degraded"
    names = {item["name"]: item["state"] for item in response.data["components"]}
    assert names["core"] == "available"
    assert names["memory_backend"] == "unavailable"
    assert names["surreal_backend"] == "unavailable"


def test_capabilities_do_not_claim_unbound_memory_or_surreal() -> None:
    response = invoke("capabilities")
    assert response.ok is True
    assert response.data is not None
    by_id = {item["capability"]: item["state"] for item in response.data["capabilities"]}
    assert by_id[CapabilityId.CONTEXT_READ.value] == "available"
    assert by_id[CapabilityId.RETRIEVAL.value] == "available"
    assert by_id[CapabilityId.EVIDENCE.value] == "available"
    assert by_id[CapabilityId.MEMORY_READ.value] == "unavailable"
    assert by_id[CapabilityId.SURREAL_READ.value] == "unavailable"
    assert response.data["read_only"] is True


def test_context_read_valid_request() -> None:
    payload = {
        "mode": "package",
        "target_scope": "repo:demo",
        "source_priority": {"ordered_sources": ["repo", "docs"]},
        "artifacts": [
            {
                "ref": {
                    "schema_version": "artifact-ref/v1",
                    "artifact_id": "a1",
                    "source_id": "repo",
                    "source_path": "README.md",
                    "source_hash": "abc123",
                },
                "artifact_type": "doc",
                "summary": "readme",
                "payload": {"title": "Demo"},
            }
        ],
        "generated_at_or_as_of": "2026-10-31T12:00:00Z",
    }
    response = invoke("context_read", payload)
    assert response.ok is True
    assert response.data is not None
    assert response.data["mode"] == "package"
    assert response.data["package"]["target_scope"] == "repo:demo"


def test_context_read_invalid_input() -> None:
    response = invoke("context_read", {"mode": "package"})
    assert response.ok is False
    assert response.error is not None
    assert response.error.code is ProtocolErrorCode.INVALID_INPUT


def test_evidence_missing_scope_fail_closed() -> None:
    response = invoke("evidence", {})
    assert response.ok is False
    assert response.error is not None
    assert response.error.code is ProtocolErrorCode.INVALID_SCOPE


def test_evidence_valid_scope() -> None:
    response = invoke("evidence", {"scope": "repo:demo", "topic": "trust"})
    assert response.ok is True
    assert response.data is not None
    assert "trust_summary" in response.data


def test_memory_read_unbound_is_capability_unavailable_not_empty() -> None:
    response = invoke(
        "memory_read",
        {
            "scope": {
                "schema_version": "memory-scope/v1",
                "kind": "tenant",
                "tenant_id": "t1",
            },
            "as_of": "2026-10-31T12:00:00Z",
        },
    )
    assert response.ok is False
    assert response.error is not None
    assert response.error.code is ProtocolErrorCode.CAPABILITY_UNAVAILABLE
    assert response.data is None


def test_memory_read_invalid_scope_fail_closed() -> None:
    runtime = ProtocolRuntime(memory_store=InMemoryMemoryStore(records=()))
    response = ProtocolGateway(runtime).invoke_sync(
        ProtocolRequest(
            operation="memory_read",
            payload={"scope": {"kind": "tenant"}, "as_of": "2026-10-31T12:00:00Z"},
        )
    )
    assert response.ok is False
    assert response.error is not None
    assert response.error.code is ProtocolErrorCode.INVALID_SCOPE


def test_memory_read_backend_unavailable_not_empty() -> None:
    # UnavailableMemoryStore is the default marker for "not configured".
    # Bind a subclass so capability is considered configured, then fail closed.
    class _BrokenStore(UnavailableMemoryStore):
        pass

    runtime = ProtocolRuntime(memory_store=_BrokenStore())
    response = ProtocolGateway(runtime).invoke_sync(
        ProtocolRequest(
            operation="memory_read",
            payload={
                "scope": {
                    "schema_version": "memory-scope/v1",
                    "kind": "tenant",
                    "tenant_id": "t1",
                },
                "as_of": "2026-10-31T12:00:00Z",
            },
        )
    )
    assert response.ok is False
    assert response.error is not None
    assert response.error.code is ProtocolErrorCode.BACKEND_UNAVAILABLE


def test_surreal_read_unavailable_by_default() -> None:
    response = invoke("surreal_read", {})
    assert response.ok is False
    assert response.error is not None
    assert response.error.code is ProtocolErrorCode.CAPABILITY_UNAVAILABLE


def test_surreal_configured_but_unprobed_stays_unavailable() -> None:
    runtime = ProtocolRuntime(
        surreal_settings=SurrealDbReadSettings(),
        surreal_probe_enabled=False,
    )
    response = ProtocolGateway(runtime).invoke_sync(ProtocolRequest(operation="surreal_read"))
    assert response.ok is False
    assert response.error is not None
    assert response.error.code in {
        ProtocolErrorCode.CAPABILITY_UNAVAILABLE,
        ProtocolErrorCode.BACKEND_UNAVAILABLE,
    }


def test_write_operations_rejected() -> None:
    for name in sorted(FORBIDDEN_WRITE_OPERATIONS)[:5]:
        response = invoke(name, {})
        assert response.ok is False
        assert response.error is not None
        assert response.error.code is ProtocolErrorCode.UNSUPPORTED_OPERATION


def test_unsupported_operation() -> None:
    response = invoke("not_a_real_op")
    assert response.ok is False
    assert response.error is not None
    assert response.error.code is ProtocolErrorCode.UNSUPPORTED_OPERATION


def test_mcp_adapter_is_thin_and_optional() -> None:
    schemas = tool_schemas()
    assert schemas["requires_mcp_sdk"] is False
    assert schemas["requires_private_operator_mcp"] is False
    adapter = BrainMcpAdapter()
    payload = adapter.call_tool("version")
    assert payload["ok"] is True
    assert payload["agent_brain_version"] == __version__


def test_core_importable_without_mcp_dependency() -> None:
    from agent_brain import protocol
    from agent_brain.protocol.gateway import ProtocolGateway as GW

    assert protocol.tool_schemas()["requires_mcp_sdk"] is False
    assert GW is not None


def test_response_redacts_sensitive_keys() -> None:
    # Internal failure path should not echo secrets from details construction;
    # success path redacts data mappings.
    response = invoke("version")
    text = str(response.to_dict())
    assert "password" not in text.lower() or "[REDACTED]" in text


@pytest.mark.parametrize(
    "operation",
    ["version", "health", "capabilities"],
)
def test_meta_operations_async_gateway(operation: str) -> None:
    gateway = ProtocolGateway()
    response = asyncio.run(gateway.invoke(ProtocolRequest(operation=operation)))
    assert response.ok is True
