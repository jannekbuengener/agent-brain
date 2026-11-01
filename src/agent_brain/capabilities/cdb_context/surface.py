"""Thin ``cdb_context`` capability composers over existing Agent Brain surfaces.

No second context/retrieval/evidence engine. Protocol operations are preferred;
``required_reads`` composes the existing product-neutral resolver with the CDB
profile only.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_brain.capabilities.cdb_context.profile import (
    CdbContextProfile,
    default_cdb_context_profile,
)
from agent_brain.capabilities.freshness import LIMITATION_NO_EVIDENCE
from agent_brain.context import resolve_required_reads
from agent_brain.protocol.errors import ProtocolError, ProtocolErrorCode
from agent_brain.protocol.gateway import ProtocolGateway
from agent_brain.protocol.models import ProtocolRequest, ProtocolResponse


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProtocolError(
            ProtocolErrorCode.INVALID_INPUT,
            f"{field_name} must be a non-empty string",
        )
    return value.strip()


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, field_name)


def _task_or_topic(payload: Mapping[str, Any]) -> str:
    task = payload.get("task")
    topic = payload.get("topic")
    if task is not None and topic is not None:
        raise ProtocolError(
            ProtocolErrorCode.INVALID_INPUT,
            "provide either task or topic, not both",
        )
    if task is not None:
        return _require_text(task, "task")
    if topic is not None:
        return _require_text(topic, "topic")
    # Accept task_scope as alias used by existing briefing contracts.
    if payload.get("task_scope") is not None:
        return _require_text(payload.get("task_scope"), "task_scope")
    raise ProtocolError(
        ProtocolErrorCode.INVALID_INPUT,
        "task or topic is required",
    )


def invoke_briefing(
    payload: Mapping[str, Any],
    *,
    gateway: ProtocolGateway,
    profile: CdbContextProfile | None = None,
) -> ProtocolResponse:
    """Compose ``context_read`` mode=briefing with CDB profile defaults."""
    data = dict(payload)
    profile = profile or default_cdb_context_profile()
    scope = _task_or_topic(data)
    task_id = _optional_text(data.get("task_id"), "task_id") or f"cdb_context:{scope}"
    protocol_payload: dict[str, Any] = {
        "mode": "briefing",
        "task_id": task_id,
        "task_scope": scope,
        "operation_mode": _optional_text(data.get("operation_mode"), "operation_mode")
        or "read_only",
        "requested_depth": _optional_text(data.get("requested_depth"), "requested_depth")
        or "standard",
        "target_issue": _optional_text(data.get("target_issue"), "target_issue"),
        "target_paths": list(data.get("target_paths") or ()),
        "target_symbols": list(data.get("target_symbols") or ()),
        "target_concepts": list(data.get("target_concepts") or ()),
        "risk_level": _optional_text(data.get("risk_level"), "risk_level") or "medium",
        "guardrails": list(
            dict.fromkeys([*profile.guardrails, *(data.get("guardrails") or ())])
        ),
    }
    if data.get("evidence_refs") is not None:
        protocol_payload["evidence_refs"] = data.get("evidence_refs")
    response = gateway.invoke_sync(
        ProtocolRequest(operation="context_read", payload=protocol_payload)
    )
    if not response.ok or response.data is None:
        return response
    enriched = dict(response.data)
    enriched["profile"] = {
        "repository_identity": profile.repository_identity,
        "source_priority": list(profile.source_priority.ordered_sources),
    }
    enriched["capability"] = "cdb_context.briefing"
    return ProtocolResponse(
        ok=True,
        operation=response.operation,
        agent_brain_version=response.agent_brain_version,
        protocol_schema=response.protocol_schema,
        data=enriched,
        limitations=response.limitations,
        request_id=response.request_id,
    )


def invoke_search(
    payload: Mapping[str, Any],
    *,
    gateway: ProtocolGateway,
    profile: CdbContextProfile | None = None,
) -> ProtocolResponse:
    """Compose ``retrieval`` with CDB source-priority defaults; no core ranking fork."""
    data = dict(payload)
    profile = profile or default_cdb_context_profile()
    query_text = data.get("query")
    scope = data.get("scope")
    if scope is not None and (not isinstance(scope, str) or not scope.strip()):
        raise ProtocolError(ProtocolErrorCode.INVALID_SCOPE, "scope must be a non-empty string")
    default_source_id = (
        str(scope).strip()
        if isinstance(scope, str) and scope.strip()
        else profile.repository_identity
    )

    if isinstance(query_text, str):
        text = query_text.strip()
        if not text:
            raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, "query must be a non-empty string")
        query_obj: dict[str, Any] = {
            "schema_version": "retrieval-query/v1",
            "query_id": _optional_text(data.get("query_id"), "query_id") or "cdb_context.search",
            "query_text": text,
            "source_id": _optional_text(data.get("source_id"), "source_id") or default_source_id,
        }
    elif isinstance(query_text, Mapping):
        query_obj = dict(query_text)
        query_obj.setdefault("schema_version", "retrieval-query/v1")
        query_obj.setdefault("source_id", default_source_id)
    else:
        raise ProtocolError(
            ProtocolErrorCode.INVALID_INPUT,
            "query must be a non-empty string or retrieval query object",
        )

    protocol_payload: dict[str, Any] = {
        "query": query_obj,
        "records": list(data.get("records") or ()),
        "edges": list(data.get("edges") or ()),
        "source_priority": data.get("source_priority")
        or {"ordered_sources": list(profile.source_priority.ordered_sources)},
    }
    if data.get("policy") is not None:
        protocol_payload["policy"] = data.get("policy")

    response = gateway.invoke_sync(
        ProtocolRequest(operation="retrieval", payload=protocol_payload)
    )
    if not response.ok or response.data is None:
        return response
    enriched = dict(response.data)
    enriched["capability"] = "cdb_context.search"
    enriched["profile"] = {
        "repository_identity": profile.repository_identity,
        "source_priority": list(profile.source_priority.ordered_sources),
    }
    if scope is not None:
        enriched["scope"] = str(scope).strip()
    return ProtocolResponse(
        ok=True,
        operation=response.operation,
        agent_brain_version=response.agent_brain_version,
        protocol_schema=response.protocol_schema,
        data=enriched,
        limitations=response.limitations,
        request_id=response.request_id,
    )


def invoke_required_reads(
    payload: Mapping[str, Any],
    *,
    profile: CdbContextProfile | None = None,
) -> dict[str, object]:
    """Resolve CDB required reads via existing ``resolve_required_reads``."""
    data = dict(payload)
    profile = profile or default_cdb_context_profile()
    assert profile.required_reads_profile is not None
    scope = _task_or_topic(data)
    available_raw = data.get("available_paths")
    available_paths: frozenset[str] | None
    if available_raw is None:
        available_paths = None
    elif isinstance(available_raw, (list, tuple, set, frozenset)):
        available_paths = frozenset(str(item) for item in available_raw)
    else:
        raise ProtocolError(
            ProtocolErrorCode.INVALID_INPUT,
            "available_paths must be a list when provided",
        )

    reads = resolve_required_reads(
        profile=profile.required_reads_profile,
        task_scope=scope,
        operation_mode=_optional_text(data.get("operation_mode"), "operation_mode")
        or "read_only",
        target_issue=_optional_text(data.get("target_issue"), "target_issue"),
        target_paths=tuple(str(item) for item in (data.get("target_paths") or ())),
        target_symbols=tuple(str(item) for item in (data.get("target_symbols") or ())),
        target_concepts=tuple(str(item) for item in (data.get("target_concepts") or ())),
        available_paths=available_paths,
    )
    return {
        "capability": "cdb_context.required_reads",
        "repository_identity": profile.repository_identity,
        "task_scope": scope,
        "required_reads": [item.to_dict() for item in reads],
        "source_priority": list(profile.source_priority.ordered_sources),
    }


def invoke_evidence(
    payload: Mapping[str, Any],
    *,
    gateway: ProtocolGateway,
    profile: CdbContextProfile | None = None,
) -> ProtocolResponse:
    """Compose protocol ``evidence``; missing evidence stays unconfirmed."""
    data = dict(payload)
    profile = profile or default_cdb_context_profile()

    # Accept ref | claim | query aliases from the #73 surface.
    scope = data.get("scope")
    if scope is None:
        for key in ("ref", "claim", "query"):
            if data.get(key) is not None:
                scope = data.get(key)
                break
    if scope is None or (isinstance(scope, str) and not scope.strip()):
        raise ProtocolError(
            ProtocolErrorCode.INVALID_SCOPE,
            "evidence requires ref, claim, query, or scope",
        )
    if not isinstance(scope, str):
        raise ProtocolError(ProtocolErrorCode.INVALID_SCOPE, "evidence scope must be a string")

    protocol_payload: dict[str, Any] = {
        "scope": scope.strip(),
        "topic": _optional_text(data.get("topic"), "topic"),
    }
    if data.get("schema_version") is not None:
        protocol_payload["schema_version"] = data.get("schema_version")

    response = gateway.invoke_sync(
        ProtocolRequest(operation="evidence", payload=protocol_payload)
    )
    if not response.ok or response.data is None:
        return response

    enriched = dict(response.data)
    enriched["capability"] = "cdb_context.evidence"
    enriched["profile"] = {"repository_identity": profile.repository_identity}
    limitations = list(response.limitations)
    trust = enriched.get("trust_summary")
    # Preserve structured evidence; never upgrade missing evidence to confirmed.
    if isinstance(trust, Mapping):
        level = str(trust.get("trust_level") or "").lower()
        sufficiency = str(trust.get("evidence_sufficiency") or "").lower()
        blocking = trust.get("blocking_findings") or ()
        if level in {"insufficient", "unknown", "none", ""} or sufficiency == "insufficient":
            # Missing / insufficient evidence must never read as confirmed.
            limitations.append(LIMITATION_NO_EVIDENCE)
            enriched["evidence_state"] = "NO_EVIDENCE"
            enriched["confirmed"] = False
        else:
            enriched.setdefault("evidence_state", "STRUCTURED")
            enriched["confirmed"] = level == "strong" and not blocking
    else:
        limitations.append(LIMITATION_NO_EVIDENCE)
        enriched["evidence_state"] = "NO_EVIDENCE"
        enriched["confirmed"] = False

    return ProtocolResponse(
        ok=True,
        operation=response.operation,
        agent_brain_version=response.agent_brain_version,
        protocol_schema=response.protocol_schema,
        data=enriched,
        limitations=tuple(dict.fromkeys(limitations)),
        request_id=response.request_id,
    )


__all__ = [
    "invoke_briefing",
    "invoke_evidence",
    "invoke_required_reads",
    "invoke_search",
]
