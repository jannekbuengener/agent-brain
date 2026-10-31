"""Domain operation handlers for the public protocol surface.

Each handler delegates to existing core/application owners. No second domain
logic lives here; transport adapters must call these through the gateway.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from agent_brain.context import (
    ContextArtifact,
    ContextPackageRequest,
    build_briefing,
    build_context_package,
)
from agent_brain.context.briefing import BriefingRequest
from agent_brain.contracts import ArtifactRef, EvidenceRef, GraphEdge, IndexRecord
from agent_brain.core.source_priority import SourcePriority
from agent_brain.evidence import TrustRequest, build_trust_summary
from agent_brain.evidence.contract import TRUST_REQUEST_SCHEMA
from agent_brain.memory import (
    InvalidMemoryScope,
    MemoryEntryCatalog,
    MemoryReadService,
    MemoryScope,
    StoreAvailability,
)
from agent_brain.memory.types import MEMORY_RECALL_QUERY_SCHEMA, MemoryRecallQuery
from agent_brain.protocol.errors import ProtocolError, ProtocolErrorCode
from agent_brain.protocol.models import (
    PROTOCOL_SCHEMA,
    CapabilityId,
    CapabilityReport,
    CapabilityState,
    CapabilityStatus,
    ComponentHealth,
    HealthReport,
    HealthState,
    agent_brain_version_metadata,
)
from agent_brain.protocol.runtime import ProtocolRuntime
from agent_brain.retrieval import RetrievalPolicy, RetrievalQuery, run_retrieval
from agent_brain.retrieval.contract import RETRIEVAL_POLICY_SCHEMA, RETRIEVAL_QUERY_SCHEMA

_DEFAULT_RETRIEVAL_POLICY = RetrievalPolicy(
    schema_version=RETRIEVAL_POLICY_SCHEMA,
    policy_id="protocol-default",
    factor_weights={
        "lexical": 0.4,
        "semantic": 0.2,
        "graph": 0.2,
        "source_priority": 0.1,
        "evidence_provenance": 0.1,
    },
    default_factor_value=0.0,
    tie_break_keys=("record_id",),
    source_priority=("repo",),
)


def _require_mapping(payload: Mapping[str, Any], field_name: str = "payload") -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, f"{field_name} must be a mapping")
    return dict(payload)


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ProtocolError(
            ProtocolErrorCode.INVALID_INPUT,
            f"{field_name} must be a non-empty string when provided",
        )
    return value.strip()


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProtocolError(
            ProtocolErrorCode.INVALID_INPUT,
            f"{field_name} must be a non-empty string",
        )
    return value.strip()


def operation_version(_payload: Mapping[str, Any], _runtime: ProtocolRuntime) -> dict[str, object]:
    return agent_brain_version_metadata()


async def _store_health_state(runtime: ProtocolRuntime) -> ComponentHealth:
    try:
        health = await runtime.memory_store.health()
    except Exception as exc:  # noqa: BLE001 - boundary: map to structured health
        return ComponentHealth(
            name="memory_backend",
            state=HealthState.UNAVAILABLE,
            detail=str(exc) or "memory health probe failed",
        )
    if health.availability is StoreAvailability.AVAILABLE:
        return ComponentHealth(name="memory_backend", state=HealthState.AVAILABLE)
    return ComponentHealth(
        name="memory_backend",
        state=HealthState.UNAVAILABLE,
        detail=health.detail or "memory store unavailable",
    )


async def _knowledge_health_state(runtime: ProtocolRuntime) -> ComponentHealth:
    try:
        health = await runtime.knowledge_store.health()
    except Exception as exc:  # noqa: BLE001
        return ComponentHealth(
            name="knowledge_backend",
            state=HealthState.UNAVAILABLE,
            detail=str(exc) or "knowledge health probe failed",
        )
    if health.availability is StoreAvailability.AVAILABLE:
        return ComponentHealth(name="knowledge_backend", state=HealthState.AVAILABLE)
    return ComponentHealth(
        name="knowledge_backend",
        state=HealthState.UNAVAILABLE,
        detail=health.detail or "knowledge store unavailable",
    )


async def _surreal_health_state(runtime: ProtocolRuntime) -> ComponentHealth:
    if not runtime.surreal_configured:
        return ComponentHealth(
            name="surreal_backend",
            state=HealthState.UNAVAILABLE,
            detail="surreal settings not configured",
        )
    if not runtime.surreal_probe_enabled:
        return ComponentHealth(
            name="surreal_backend",
            state=HealthState.UNAVAILABLE,
            detail="surreal probe disabled; capability unavailable until probed",
        )
    settings = runtime.surreal_settings
    assert settings is not None
    try:
        from agent_brain.surrealdb.knowledge_store import SurrealKnowledgeStore

        store = SurrealKnowledgeStore(settings=settings)
        health = await store.health()
    except Exception as exc:  # noqa: BLE001
        return ComponentHealth(
            name="surreal_backend",
            state=HealthState.UNAVAILABLE,
            detail=str(exc) or "surreal health probe failed",
        )
    if health.availability is StoreAvailability.AVAILABLE:
        return ComponentHealth(name="surreal_backend", state=HealthState.AVAILABLE)
    return ComponentHealth(
        name="surreal_backend",
        state=HealthState.UNAVAILABLE,
        detail=health.detail or "surreal backend unavailable",
    )


async def operation_health(
    _payload: Mapping[str, Any],
    runtime: ProtocolRuntime,
) -> dict[str, object]:
    core = ComponentHealth(
        name="core",
        state=HealthState.AVAILABLE,
        detail="application surface ready",
    )
    memory = await _store_health_state(runtime)
    knowledge = await _knowledge_health_state(runtime)
    surreal = await _surreal_health_state(runtime)
    components = (core, memory, knowledge, surreal)
    limitations = tuple(
        sorted(
            {
                f"{item.name}_unavailable"
                for item in components
                if item.state is HealthState.UNAVAILABLE and item.name != "core"
            }
        )
    )
    if core.state is HealthState.UNAVAILABLE:
        overall = HealthState.UNAVAILABLE
    elif any(item.state is HealthState.UNAVAILABLE for item in components[1:]):
        overall = HealthState.DEGRADED
    else:
        overall = HealthState.AVAILABLE

    report = HealthReport(
        schema_version="agent-brain-health/v1",
        overall=overall,
        components=components,
        limitations=limitations,
    )
    return report.to_dict()


def _capability_statuses(runtime: ProtocolRuntime, *, surreal_available: bool) -> CapabilityReport:
    memory_available = runtime.memory_backend_configured
    statuses = (
        CapabilityStatus(
            capability=CapabilityId.CONTEXT_READ,
            state=CapabilityState.AVAILABLE,
            detail="deterministic context package / briefing",
        ),
        CapabilityStatus(
            capability=CapabilityId.RETRIEVAL,
            state=CapabilityState.AVAILABLE,
            detail="hybrid retrieval over supplied index records",
        ),
        CapabilityStatus(
            capability=CapabilityId.EVIDENCE,
            state=CapabilityState.AVAILABLE,
            detail="trust summary over supplied evidence inputs",
        ),
        CapabilityStatus(
            capability=CapabilityId.MEMORY_READ,
            state=CapabilityState.AVAILABLE if memory_available else CapabilityState.UNAVAILABLE,
            detail=None
            if memory_available
            else "no memory store bound; default runtime is unavailable",
        ),
        CapabilityStatus(
            capability=CapabilityId.SURREAL_READ,
            state=CapabilityState.AVAILABLE if surreal_available else CapabilityState.UNAVAILABLE,
            detail=None
            if surreal_available
            else "surreal read backend not configured or not probed healthy",
        ),
    )
    return CapabilityReport(
        schema_version="agent-brain-capabilities/v1",
        capabilities=statuses,
        read_only=True,
    )


async def operation_capabilities(
    _payload: Mapping[str, Any],
    runtime: ProtocolRuntime,
) -> dict[str, object]:
    surreal = await _surreal_health_state(runtime)
    report = _capability_statuses(
        runtime,
        surreal_available=surreal.state is HealthState.AVAILABLE,
    )
    return report.to_dict()


def _parse_source_priority(raw: object) -> SourcePriority:
    if isinstance(raw, SourcePriority):
        return raw
    if isinstance(raw, Mapping) and "ordered_sources" in raw:
        sources = raw["ordered_sources"]
    else:
        sources = raw
    if not isinstance(sources, (list, tuple)) or not sources:
        raise ProtocolError(
            ProtocolErrorCode.INVALID_INPUT,
            "source_priority.ordered_sources must be a non-empty list",
        )
    try:
        return SourcePriority(ordered_sources=tuple(str(item) for item in sources))
    except (TypeError, ValueError) as exc:
        raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, str(exc)) from exc


def _parse_context_artifacts(raw: object) -> tuple[ContextArtifact, ...]:
    if not isinstance(raw, (list, tuple)):
        raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, "artifacts must be a list")
    artifacts: list[ContextArtifact] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, "artifact entries must be objects")
        ref_raw = item.get("ref")
        if not isinstance(ref_raw, Mapping):
            raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, "artifact.ref must be an object")
        try:
            ref = ArtifactRef.from_dict(dict(ref_raw))
            artifacts.append(
                ContextArtifact(
                    ref=ref,
                    artifact_type=_required_text(item.get("artifact_type"), "artifact_type"),
                    summary=_optional_text(item.get("summary"), "summary"),
                    payload=dict(item.get("payload") or {}),
                )
            )
        except (TypeError, ValueError) as exc:
            raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, str(exc)) from exc
    return tuple(artifacts)


def _parse_evidence_refs(raw: object) -> tuple[EvidenceRef, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, (list, tuple)):
        raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, "evidence_refs must be a list")
    refs: list[EvidenceRef] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise ProtocolError(
                ProtocolErrorCode.INVALID_INPUT,
                "evidence_refs entries must be objects",
            )
        try:
            refs.append(EvidenceRef.from_dict(dict(item)))
        except (TypeError, ValueError) as exc:
            raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, str(exc)) from exc
    return tuple(refs)


def operation_context_read(payload: Mapping[str, Any], _runtime: ProtocolRuntime) -> dict[str, object]:
    data = _require_mapping(payload)
    mode = _optional_text(data.get("mode"), "mode") or "package"
    if mode not in {"package", "briefing"}:
        raise ProtocolError(
            ProtocolErrorCode.INVALID_INPUT,
            "mode must be 'package' or 'briefing'",
        )
    try:
        if mode == "briefing":
            request = BriefingRequest(
                task_id=_required_text(data.get("task_id"), "task_id"),
                task_scope=_required_text(data.get("task_scope"), "task_scope"),
                target_issue=_optional_text(data.get("target_issue"), "target_issue"),
                requested_depth=_optional_text(data.get("requested_depth"), "requested_depth")
                or "standard",
                operation_mode=_required_text(
                    data.get("operation_mode", "read_only"),
                    "operation_mode",
                ),
                target_paths=tuple(str(item) for item in (data.get("target_paths") or ())),
                target_symbols=tuple(str(item) for item in (data.get("target_symbols") or ())),
                target_concepts=tuple(str(item) for item in (data.get("target_concepts") or ())),
                risk_level=_optional_text(data.get("risk_level"), "risk_level") or "medium",
            )
            envelope = build_briefing(
                request,
                context_package=None,
                evidence_refs=_parse_evidence_refs(data.get("evidence_refs")),
                guardrails=tuple(str(item) for item in (data.get("guardrails") or ())),
            )
            return {"mode": mode, "briefing": envelope.to_dict()}

        request = ContextPackageRequest(
            target_scope=_required_text(data.get("target_scope"), "target_scope"),
            artifacts=_parse_context_artifacts(data.get("artifacts") or ()),
            source_priority=_parse_source_priority(data.get("source_priority")),
            required_reads=tuple(data.get("required_reads") or ()),
            ranked_context=data.get("ranked_context"),
            evidence_refs=_parse_evidence_refs(data.get("evidence_refs")),
            decision_refs=tuple(str(item) for item in (data.get("decision_refs") or ())),
            guardrails=tuple(str(item) for item in (data.get("guardrails") or ())),
            generated_at_or_as_of=_optional_text(
                data.get("generated_at_or_as_of"),
                "generated_at_or_as_of",
            ),
        )
        package = build_context_package(request)
        return {"mode": mode, "package": package.to_dict()}
    except ProtocolError:
        raise
    except (TypeError, ValueError) as exc:
        raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, str(exc)) from exc


def _parse_index_records(raw: object) -> tuple[IndexRecord, ...]:
    if not isinstance(raw, (list, tuple)):
        raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, "records must be a list")
    records: list[IndexRecord] = []
    for item in raw:
        if isinstance(item, IndexRecord):
            records.append(item)
            continue
        if not isinstance(item, Mapping):
            raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, "record entries must be objects")
        try:
            records.append(IndexRecord.from_dict(dict(item)))
        except (TypeError, ValueError) as exc:
            raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, str(exc)) from exc
    return tuple(records)


def _parse_edges(raw: object) -> tuple[GraphEdge, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, (list, tuple)):
        raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, "edges must be a list")
    edges: list[GraphEdge] = []
    for item in raw:
        if isinstance(item, GraphEdge):
            edges.append(item)
            continue
        if not isinstance(item, Mapping):
            raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, "edge entries must be objects")
        try:
            edges.append(GraphEdge.from_dict(dict(item)))
        except (TypeError, ValueError) as exc:
            raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, str(exc)) from exc
    return tuple(edges)


def operation_retrieval(payload: Mapping[str, Any], _runtime: ProtocolRuntime) -> dict[str, object]:
    data = _require_mapping(payload)
    query_raw = data.get("query")
    if not isinstance(query_raw, Mapping):
        raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, "query must be an object")
    try:
        query = RetrievalQuery.from_dict(
            {
                "schema_version": query_raw.get("schema_version", RETRIEVAL_QUERY_SCHEMA),
                **dict(query_raw),
            }
        )
        policy_raw = data.get("policy")
        if policy_raw is None:
            policy = _DEFAULT_RETRIEVAL_POLICY
        else:
            policy = RetrievalPolicy.from_dict(dict(policy_raw))
        source_priority_raw = data.get("source_priority")
        source_priority = (
            _parse_source_priority(source_priority_raw)
            if source_priority_raw is not None
            else SourcePriority(ordered_sources=tuple(policy.source_priority) or ("repo",))
        )
        result = run_retrieval(
            query,
            records=_parse_index_records(data.get("records") or ()),
            edges=_parse_edges(data.get("edges")),
            policy=policy,
            source_priority=source_priority,
        )
        return {"result": result.to_dict()}
    except ProtocolError:
        raise
    except (TypeError, ValueError) as exc:
        raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, str(exc)) from exc


def operation_evidence(payload: Mapping[str, Any], _runtime: ProtocolRuntime) -> dict[str, object]:
    data = _require_mapping(payload)
    scope = data.get("scope")
    if scope is None or (isinstance(scope, str) and not scope.strip()):
        raise ProtocolError(
            ProtocolErrorCode.INVALID_SCOPE,
            "evidence requires an explicit non-empty scope",
        )
    if not isinstance(scope, str):
        raise ProtocolError(ProtocolErrorCode.INVALID_SCOPE, "scope must be a string")
    try:
        request = TrustRequest(
            schema_version=str(data.get("schema_version", TRUST_REQUEST_SCHEMA)),
            scope=scope.strip(),
            topic=_optional_text(data.get("topic"), "topic"),
        )
        summary = build_trust_summary(request=request)
        return {"trust_summary": summary.to_dict()}
    except ProtocolError:
        raise
    except (TypeError, ValueError) as exc:
        message = str(exc)
        if "scope" in message.lower():
            raise ProtocolError(ProtocolErrorCode.INVALID_SCOPE, message) from exc
        raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, message) from exc


def _parse_memory_scope(raw: object) -> MemoryScope:
    if raw is None:
        raise ProtocolError(
            ProtocolErrorCode.INVALID_SCOPE,
            "memory_read requires an explicit scope",
        )
    if isinstance(raw, MemoryScope):
        return raw
    if not isinstance(raw, Mapping):
        raise ProtocolError(ProtocolErrorCode.INVALID_SCOPE, "scope must be an object")
    try:
        return MemoryScope.from_dict(dict(raw))
    except InvalidMemoryScope as exc:
        raise ProtocolError(ProtocolErrorCode.INVALID_SCOPE, str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise ProtocolError(ProtocolErrorCode.INVALID_SCOPE, str(exc)) from exc


def _parse_as_of(raw: object) -> datetime:
    if raw is None:
        raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, "as_of is required")
    if isinstance(raw, datetime):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, "as_of must be an ISO-8601 string")
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, f"invalid as_of: {raw}") from exc


def _serialize_memory_read_result(result: Any) -> dict[str, object]:
    items: list[dict[str, object]] = []
    for item in result.items:
        entry_payload = item.entry.to_dict()
        item_payload: dict[str, object] = {
            "schema_version": item.schema_version,
            "entry": entry_payload,
            "resolution_state": item.resolution_state.value,
            "reason_codes": list(item.reason_codes),
            "admissible_as_context": item.admissible_as_context,
            "artifact_kind": item.artifact_kind.value,
        }
        if item.live_revalidation is not None:
            item_payload["live_revalidation"] = item.live_revalidation.to_dict()
        if item.explanation is not None:
            item_payload["explanation"] = item.explanation
        items.append(item_payload)
    payload: dict[str, object] = {
        "schema_version": result.schema_version,
        "availability": result.availability.value,
        "items": items,
        "limitations": list(result.limitations),
        "artifact_kind": result.artifact_kind.value,
    }
    if result.detail is not None:
        payload["detail"] = result.detail
    if result.as_of is not None:
        payload["as_of"] = result.as_of.isoformat() + "Z"
    return payload


async def operation_memory_read(
    payload: Mapping[str, Any],
    runtime: ProtocolRuntime,
) -> dict[str, object]:
    data = _require_mapping(payload)
    if not runtime.memory_backend_configured:
        raise ProtocolError(
            ProtocolErrorCode.CAPABILITY_UNAVAILABLE,
            "memory_read capability unavailable: no memory store bound",
            details={"capability": CapabilityId.MEMORY_READ.value},
        )
    scope = _parse_memory_scope(data.get("scope"))
    as_of = _parse_as_of(data.get("as_of"))
    try:
        query = MemoryRecallQuery(
            schema_version=str(data.get("schema_version", MEMORY_RECALL_QUERY_SCHEMA)),
            query_id=_required_text(data.get("query_id", "protocol-memory-read"), "query_id"),
            scope=scope,
            subject_ref=_optional_text(data.get("subject_ref"), "subject_ref"),
            limit=int(data.get("limit", 20)),
            text_query=_optional_text(data.get("text_query"), "text_query"),
        )
        service = MemoryReadService(
            store=runtime.memory_store,
            catalog=MemoryEntryCatalog(),
        )
        result = await service.recall(query, as_of=as_of)
    except InvalidMemoryScope as exc:
        raise ProtocolError(ProtocolErrorCode.INVALID_SCOPE, str(exc)) from exc
    except ProtocolError:
        raise
    except (TypeError, ValueError) as exc:
        raise ProtocolError(ProtocolErrorCode.INVALID_INPUT, str(exc)) from exc

    if result.availability is StoreAvailability.UNAVAILABLE:
        raise ProtocolError(
            ProtocolErrorCode.BACKEND_UNAVAILABLE,
            result.detail or "memory backend unavailable",
            details={
                "capability": CapabilityId.MEMORY_READ.value,
                "limitations": list(result.limitations),
            },
        )
    return {"result": _serialize_memory_read_result(result)}


async def operation_surreal_read(
    payload: Mapping[str, Any],
    runtime: ProtocolRuntime,
) -> dict[str, object]:
    _ = _require_mapping(payload)
    surreal = await _surreal_health_state(runtime)
    if surreal.state is not HealthState.AVAILABLE:
        raise ProtocolError(
            ProtocolErrorCode.CAPABILITY_UNAVAILABLE
            if not runtime.surreal_configured
            else ProtocolErrorCode.BACKEND_UNAVAILABLE,
            surreal.detail or "surreal_read unavailable",
            details={"capability": CapabilityId.SURREAL_READ.value},
        )
    return {
        "capability": CapabilityId.SURREAL_READ.value,
        "state": HealthState.AVAILABLE.value,
        "message": (
            "surreal read backend available; use typed KnowledgeStore/MemoryStore ports"
        ),
        "protocol_schema": PROTOCOL_SCHEMA,
    }


async def dispatch_operation(
    operation: str,
    payload: Mapping[str, Any],
    runtime: ProtocolRuntime,
) -> dict[str, object]:
    if operation == "version":
        return operation_version(payload, runtime)
    if operation == "health":
        return await operation_health(payload, runtime)
    if operation == "capabilities":
        return await operation_capabilities(payload, runtime)
    if operation == CapabilityId.CONTEXT_READ.value:
        return operation_context_read(payload, runtime)
    if operation == CapabilityId.RETRIEVAL.value:
        return operation_retrieval(payload, runtime)
    if operation == CapabilityId.EVIDENCE.value:
        return operation_evidence(payload, runtime)
    if operation == CapabilityId.MEMORY_READ.value:
        return await operation_memory_read(payload, runtime)
    if operation == CapabilityId.SURREAL_READ.value:
        return await operation_surreal_read(payload, runtime)
    raise ProtocolError(
        ProtocolErrorCode.UNSUPPORTED_OPERATION,
        f"unsupported operation: {operation}",
        details={"operation": operation},
    )


def dispatch_operation_sync(
    operation: str,
    payload: Mapping[str, Any],
    runtime: ProtocolRuntime,
) -> dict[str, object]:
    return asyncio.run(dispatch_operation(operation, payload, runtime))


__all__ = [
    "dispatch_operation",
    "dispatch_operation_sync",
    "operation_capabilities",
    "operation_context_read",
    "operation_evidence",
    "operation_health",
    "operation_memory_read",
    "operation_retrieval",
    "operation_surreal_read",
    "operation_version",
]
