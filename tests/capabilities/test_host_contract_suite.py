"""Shared host-adapter contract suite for ``cdb_context`` (#73 Goal 1).

Future ChatGPT / Claude Code / Cursor / OpenCode adapters should import and run
this suite against their transport binding instead of re-authoring capability
semantics. The suite exercises the host-neutral CapabilityGateway directly.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import pytest

from agent_brain import __version__
from agent_brain.capabilities import (
    AGENT_BRAIN_HEALTH,
    CAPABILITY_CONTRACT_SCHEMA,
    CAPABILITY_NAME,
    CDB_CONTEXT_BRIEFING,
    CDB_CONTEXT_EVIDENCE,
    CDB_CONTEXT_REQUIRED_READS,
    CDB_CONTEXT_SEARCH,
    FORBIDDEN_ALTERNATE_PRODUCT_NAMES,
    PRODUCT_NAME,
    REQUIRED_CAPABILITY_NAMES,
    CapabilityGateway,
    capability_tool_descriptors,
    current_capability_contract,
    prefer_live_over_persisted,
)
from agent_brain.capabilities.cdb_context import CDB_REPOSITORY_IDENTITY, CDB_SOURCE_PRIORITY
from agent_brain.contracts import ArtifactRef, IndexRecord
from agent_brain.contracts.resolution import ResolutionState
from agent_brain.protocol.errors import ProtocolErrorCode

InvokeFn = Callable[..., Any]


def _default_invoke(capability: str, payload: Mapping[str, Any] | None = None, **kwargs: Any):
    return CapabilityGateway().invoke(capability, payload, **kwargs)


def _minimal_record(source_id: str = "repo_live") -> dict[str, object]:
    ref = ArtifactRef(
        schema_version="artifact-ref/v1",
        artifact_id="art-cdb-1",
        source_id=source_id,
        source_path="docs/meta/REPOSITORY_CANON.md",
        source_hash="hash-cdb-1",
    )
    record = IndexRecord(
        schema_version="index-record/v1",
        record_id="rec-cdb-1",
        record_type="doc",
        source=ref,
        content_hash="content-cdb-1",
        attributes={"title": "repository canon", "text": "claire repository canon overview"},
    )
    return record.to_dict()


def assert_capability_identity() -> None:
    contract = current_capability_contract()
    assert contract.product_name == PRODUCT_NAME == "Agent Brain"
    assert contract.capability_name == CAPABILITY_NAME == "cdb_context"
    assert contract.contract_schema == CAPABILITY_CONTRACT_SCHEMA
    assert contract.agent_brain_version == __version__
    assert contract.read_only is True
    for forbidden in FORBIDDEN_ALTERNATE_PRODUCT_NAMES:
        assert forbidden != contract.product_name


def assert_required_capability_mappings() -> None:
    descriptors = capability_tool_descriptors()
    tools = descriptors["tools"]
    assert set(tools) == set(REQUIRED_CAPABILITY_NAMES)
    assert descriptors["product_name"] == "Agent Brain"
    assert descriptors["requires_mcp_sdk"] is False
    assert descriptors["read_only"] is True
    assert "ChatGPT" not in str(descriptors)
    assert "Claude" not in str(descriptors)
    assert "Cursor" not in str(descriptors)
    assert "OpenCode" not in str(descriptors)
    for name in REQUIRED_CAPABILITY_NAMES:
        tool = tools[name]
        assert tool["read_only"] is True
        assert tool["capability_contract_schema"] == CAPABILITY_CONTRACT_SCHEMA


def assert_health(invoke: InvokeFn = _default_invoke) -> None:
    response = invoke(AGENT_BRAIN_HEALTH, {})
    assert response.ok is True
    assert response.operation == AGENT_BRAIN_HEALTH
    assert response.data is not None
    assert response.data["overall"] in {"available", "degraded", "unavailable"}
    assert response.data["capability"] == AGENT_BRAIN_HEALTH


def assert_briefing(invoke: InvokeFn = _default_invoke) -> None:
    response = invoke(CDB_CONTEXT_BRIEFING, {"task": "architecture overview"})
    assert response.ok is True
    assert response.data is not None
    assert response.data["capability"] == CDB_CONTEXT_BRIEFING
    assert "briefing" in response.data
    assert response.data["profile"]["repository_identity"] == CDB_REPOSITORY_IDENTITY
    # Sources / evidence structure preserved when present.
    briefing = response.data["briefing"]
    assert isinstance(briefing, Mapping)
    assert "schema_version" in briefing or "briefing_id" in briefing


def assert_search(invoke: InvokeFn = _default_invoke) -> None:
    response = invoke(
        CDB_CONTEXT_SEARCH,
        {
            "query": "repository canon",
            "scope": "repo_live",
            "records": [_minimal_record()],
        },
    )
    assert response.ok is True
    assert response.data is not None
    assert response.data["capability"] == CDB_CONTEXT_SEARCH
    assert response.data["scope"] == "repo_live"
    assert "result" in response.data


def assert_required_reads(invoke: InvokeFn = _default_invoke) -> None:
    focused = invoke(CDB_CONTEXT_REQUIRED_READS, {"task": "pytest fixture contract"})
    assert focused.ok is True
    assert focused.data is not None
    paths = {item["path"] for item in focused.data["required_reads"]}
    # Minimum always present.
    assert "AGENTS.md" in paths
    assert "docs/meta/REPOSITORY_CANON.md" in paths
    # Conditional testing doc included for test-focused task.
    assert "knowledge/testing/README.md" in paths
    for item in focused.data["required_reads"]:
        assert item["source_ref"].startswith(f"github:{CDB_REPOSITORY_IDENTITY}:")

    irrelevant = invoke(CDB_CONTEXT_REQUIRED_READS, {"topic": "unrelated watercolor painting"})
    assert irrelevant.ok is True
    assert irrelevant.data is not None
    irrelevant_paths = {item["path"] for item in irrelevant.data["required_reads"]}
    # No artificial full catalog dump for irrelevant topics.
    assert "knowledge/testing/README.md" not in irrelevant_paths
    assert len(irrelevant_paths) < len(paths)


def assert_evidence(invoke: InvokeFn = _default_invoke) -> None:
    response = invoke(CDB_CONTEXT_EVIDENCE, {"claim": "repo:authority"})
    assert response.ok is True
    assert response.data is not None
    assert response.data["capability"] == CDB_CONTEXT_EVIDENCE
    assert "trust_summary" in response.data
    # Missing evidence must not be confirmed.
    assert response.data.get("confirmed") is False
    assert response.data.get("evidence_state") == "NO_EVIDENCE"
    assert "no_evidence" in response.limitations


def assert_contract_versioning(invoke: InvokeFn = _default_invoke) -> None:
    ok = invoke(AGENT_BRAIN_HEALTH, {"contract_version": CAPABILITY_CONTRACT_SCHEMA})
    assert ok.ok is True
    mismatch = invoke(AGENT_BRAIN_HEALTH, {"contract_version": "agent-brain-cdb-context-capability/v99"})
    assert mismatch.ok is False
    assert mismatch.error is not None
    assert mismatch.error.code is ProtocolErrorCode.CONTRACT_VERSION_MISMATCH


def assert_missing_capability(invoke: InvokeFn = _default_invoke) -> None:
    response = invoke("cdb_context.decision_history", {})
    assert response.ok is False
    assert response.error is not None
    assert response.error.code is ProtocolErrorCode.CAPABILITY_UNAVAILABLE


def assert_invalid_input_and_scope(invoke: InvokeFn = _default_invoke) -> None:
    bad_briefing = invoke(CDB_CONTEXT_BRIEFING, {})
    assert bad_briefing.ok is False
    assert bad_briefing.error is not None
    assert bad_briefing.error.code is ProtocolErrorCode.INVALID_INPUT

    bad_search_scope = invoke(CDB_CONTEXT_SEARCH, {"query": "x", "scope": "   "})
    assert bad_search_scope.ok is False
    assert bad_search_scope.error is not None
    assert bad_search_scope.error.code is ProtocolErrorCode.INVALID_SCOPE

    bad_evidence = invoke(CDB_CONTEXT_EVIDENCE, {})
    assert bad_evidence.ok is False
    assert bad_evidence.error is not None
    assert bad_evidence.error.code is ProtocolErrorCode.INVALID_SCOPE


def assert_write_rejected(invoke: InvokeFn = _default_invoke) -> None:
    response = invoke("remember", {"text": "secret"})
    assert response.ok is False
    assert response.error is not None
    assert response.error.code is ProtocolErrorCode.UNSUPPORTED_OPERATION


def assert_secret_redaction(invoke: InvokeFn = _default_invoke) -> None:
    # Briefing responses must not materialize credential-like text.
    secret = "password=SuperSecretPasswordValue99"
    response = invoke(
        CDB_CONTEXT_BRIEFING,
        {
            "task": "status",
            "guardrails": [secret],
        },
    )
    assert response.ok is True
    rendered = str(response.to_dict())
    assert "SuperSecretPasswordValue99" not in rendered
    assert "[REDACTED]" in rendered


def assert_live_beats_stale() -> None:
    live = {"summary": "live HEAD state", "sha": "live-sha"}
    stale = {"summary": "old persisted", "sha": "old-sha"}
    selected = prefer_live_over_persisted(
        live_payload=live,
        live_source="github_live",
        live_available=True,
        persisted_payload=stale,
        persisted_source="persisted_index",
        persisted_state=ResolutionState.STALE,
        source_priority=CDB_SOURCE_PRIORITY,
    )
    assert selected.resolution_state is ResolutionState.CURRENT
    assert selected.winning_source == "github_live"
    assert selected.payload["sha"] == "live-sha"

    degraded = prefer_live_over_persisted(
        live_payload=None,
        live_source="github_live",
        live_available=False,
        persisted_payload=stale,
        persisted_source="persisted_index",
        persisted_state=ResolutionState.STALE,
        source_priority=CDB_SOURCE_PRIORITY,
        partial=True,
    )
    assert degraded.resolution_state is ResolutionState.STALE
    assert degraded.winning_source == "persisted_index"
    assert "partial_source_state" in degraded.limitations
    assert degraded.resolution_state is not ResolutionState.CURRENT


def run_host_contract_suite(invoke: InvokeFn = _default_invoke) -> None:
    """Entry point for future host-adapter bindings."""
    assert_capability_identity()
    assert_required_capability_mappings()
    assert_health(invoke)
    assert_briefing(invoke)
    assert_search(invoke)
    assert_required_reads(invoke)
    assert_evidence(invoke)
    assert_contract_versioning(invoke)
    assert_missing_capability(invoke)
    assert_invalid_input_and_scope(invoke)
    assert_write_rejected(invoke)
    assert_secret_redaction(invoke)
    assert_live_beats_stale()


@pytest.mark.parametrize(
    "check",
    [
        assert_capability_identity,
        assert_required_capability_mappings,
        assert_health,
        assert_briefing,
        assert_search,
        assert_required_reads,
        assert_evidence,
        assert_contract_versioning,
        assert_missing_capability,
        assert_invalid_input_and_scope,
        assert_write_rejected,
        assert_secret_redaction,
        assert_live_beats_stale,
    ],
)
def test_host_contract_check(check: Callable[[], None]) -> None:
    check()


def test_run_host_contract_suite() -> None:
    run_host_contract_suite()
