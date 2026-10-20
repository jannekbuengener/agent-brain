"""Portable, deterministic Context Package v2 assembly."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from agent_brain.contracts.evidence import EvidenceRef
from agent_brain.contracts.repository import ArtifactRef
from agent_brain.core.canonical import canonical_hash, canonical_json_dumps
from agent_brain.core.redaction import redact_sensitive_mapping
from agent_brain.core.source_priority import SourcePriority
from agent_brain.core.time import Clock, utcnow

CONTEXT_PACKAGE_SCHEMA = "context-package/v2"


class ContextPackageError(ValueError):
    """Raised when portable package inputs violate the contract."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ContextPackageError(f"{field_name} must not be blank")
    return normalized


def _text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple or list of strings")
    return tuple(_required_text(item, field_name) for item in values)


def _strip_private(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _strip_private(item)
            for key, item in value.items()
            if not str(key).startswith("_")
        }
    if isinstance(value, list):
        return [_strip_private(item) for item in value]
    if isinstance(value, tuple):
        return [_strip_private(item) for item in value]
    return value


def _redact(value: Any) -> Any:
    return redact_sensitive_mapping(_strip_private(value))


@dataclass(frozen=True, slots=True)
class RedactionRecord:
    """Value-free evidence that a package field was redacted."""

    path: str
    redaction_type: str = "sensitive_value"

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "redaction_type": self.redaction_type}


def _redaction_paths(original: Any, redacted: Any, path: str = "$") -> tuple[RedactionRecord, ...]:
    records: list[RedactionRecord] = []
    if isinstance(original, Mapping) and isinstance(redacted, Mapping):
        for key, original_value in original.items():
            key_text = str(key)
            if key_text.startswith("_"):
                records.append(RedactionRecord(path=f"{path}.{key_text}", redaction_type="private_field"))
                continue
            if key_text in redacted:
                records.extend(
                    _redaction_paths(original_value, redacted[key_text], f"{path}.{key_text}")
                )
        return tuple(records)
    if isinstance(original, (list, tuple)) and isinstance(redacted, list):
        for index, original_value in enumerate(original):
            if index < len(redacted):
                records.extend(
                    _redaction_paths(original_value, redacted[index], f"{path}[{index}]")
                )
        return tuple(records)
    if original != redacted:
        records.append(RedactionRecord(path=path))
    return tuple(records)


@dataclass(frozen=True, slots=True)
class ContextArtifact:
    """Context payload attached to the stable ArtifactRef from Slice #15."""

    ref: ArtifactRef
    artifact_type: str
    summary: str | None = None
    payload: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.ref, ArtifactRef):
            raise TypeError("ref must be an ArtifactRef")
        object.__setattr__(self, "artifact_type", _required_text(self.artifact_type, "artifact_type"))
        if self.summary is not None:
            object.__setattr__(self, "summary", _required_text(self.summary, "summary"))
        if not isinstance(self.payload, Mapping):
            raise TypeError("payload must be a mapping")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "ref": self.ref.to_dict(),
            "artifact_type": self.artifact_type,
            "payload": dict(self.payload),
        }
        if self.summary is not None:
            result["summary"] = self.summary
        return result


@dataclass(frozen=True, slots=True)
class ContextPackageRequest:
    """Inputs for deterministic package assembly."""

    target_scope: str
    artifacts: tuple[ContextArtifact, ...]
    source_priority: SourcePriority
    required_reads: tuple[Mapping[str, object], ...] = ()
    ranked_context: Mapping[str, object] | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()
    decision_refs: tuple[str, ...] = ()
    guardrails: tuple[str, ...] = ()
    generated_at_or_as_of: str | None = None
    clock: Clock | None = None


@dataclass(frozen=True, slots=True)
class ContextPackage:
    schema_version: str
    package_id: str
    generated_at_or_as_of: str
    target_scope: str
    source_priority: tuple[str, ...]
    required_reads: tuple[Mapping[str, object], ...]
    artifacts: tuple[ContextArtifact, ...]
    ranked_context: Mapping[str, object] | None
    evidence_refs: tuple[EvidenceRef, ...]
    decision_refs: tuple[str, ...]
    redaction_summary: tuple[RedactionRecord, ...]
    limitations: tuple[str, ...]
    guardrails: tuple[str, ...]
    content_hash: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "package_id": self.package_id,
            "generated_at_or_as_of": self.generated_at_or_as_of,
            "target_scope": self.target_scope,
            "source_priority": list(self.source_priority),
            "required_reads": [dict(item) for item in self.required_reads],
            "artifacts": [item.to_dict() for item in self.artifacts],
            "ranked_context": dict(self.ranked_context) if self.ranked_context is not None else None,
            "evidence_refs": [item.to_dict() for item in self.evidence_refs],
            "decision_refs": list(self.decision_refs),
            "redaction_summary": [item.to_dict() for item in self.redaction_summary],
            "limitations": list(self.limitations),
            "guardrails": list(self.guardrails),
            "determinism": {
                "hash_algorithm": "canonical_sha256",
                "wall_clock_excluded": True,
                "artifact_count": len(self.artifacts),
                "content_hash": self.content_hash,
            },
        }


def _artifact_payload(artifact: ContextArtifact) -> tuple[ContextArtifact, tuple[RedactionRecord, ...]]:
    original = artifact.to_dict()
    redacted_payload = _redact(dict(artifact.payload))
    redacted_summary = _redact(artifact.summary) if artifact.summary is not None else None
    sanitized = ContextArtifact(
        ref=artifact.ref,
        artifact_type=artifact.artifact_type,
        summary=redacted_summary,
        payload=redacted_payload,
    )
    return sanitized, _redaction_paths(original, sanitized.to_dict())


def build_context_package(request: ContextPackageRequest) -> ContextPackage:
    """Assemble a deterministic, redacted package without external side effects."""
    if not isinstance(request, ContextPackageRequest):
        raise TypeError("request must be a ContextPackageRequest")
    target_scope = _required_text(request.target_scope, "target_scope")
    if not isinstance(request.source_priority, SourcePriority):
        raise TypeError("source_priority must be a SourcePriority")
    if not isinstance(request.artifacts, (tuple, list)) or not request.artifacts:
        raise ContextPackageError("artifacts must not be empty")

    artifact_pairs = [_artifact_payload(item) for item in request.artifacts]
    artifacts = tuple(sorted((item for item, _ in artifact_pairs), key=lambda item: item.ref.artifact_id))
    redaction_records = [record for _, records in artifact_pairs for record in records]

    required_reads: list[Mapping[str, object]] = []
    for index, item in enumerate(request.required_reads):
        if not isinstance(item, Mapping):
            raise TypeError("required_reads entries must be mappings")
        original = dict(item)
        redacted = _redact(original)
        redaction_records.extend(_redaction_paths(original, redacted, f"$.required_reads[{index}]"))
        required_reads.append(MappingProxyType(dict(redacted)))
    required_reads_tuple = tuple(sorted(required_reads, key=lambda item: canonical_json_dumps(dict(item))))

    if request.ranked_context is not None and not isinstance(request.ranked_context, Mapping):
        raise TypeError("ranked_context must be a mapping when present")
    ranked_context = _redact(dict(request.ranked_context)) if request.ranked_context is not None else None
    if request.ranked_context is not None:
        redaction_records.extend(
            _redaction_paths(dict(request.ranked_context), ranked_context, "$.ranked_context")
        )

    for item in request.evidence_refs:
        if not isinstance(item, EvidenceRef):
            raise TypeError("evidence_refs entries must be EvidenceRef values")
    evidence_refs = tuple(sorted(request.evidence_refs, key=lambda item: item.evidence_id))
    decision_refs = tuple(sorted(_text_tuple(request.decision_refs, "decision_refs")))
    guardrails = _text_tuple(request.guardrails, "guardrails")

    limitations: list[str] = []
    if ranked_context is None:
        limitations.append("ranked_context_not_provided")
    if not evidence_refs:
        limitations.append("evidence_refs_not_provided")
    if not decision_refs:
        limitations.append("decision_refs_not_provided")

    stable_payload = {
        "schema_version": CONTEXT_PACKAGE_SCHEMA,
        "target_scope": target_scope,
        "source_priority": list(request.source_priority.ordered_sources),
        "required_reads": [dict(item) for item in required_reads_tuple],
        "artifacts": [item.to_dict() for item in artifacts],
        "ranked_context": ranked_context,
        "evidence_refs": [item.to_dict() for item in evidence_refs],
        "decision_refs": list(decision_refs),
        "redaction_summary": [
            record.to_dict() for record in sorted(redaction_records, key=lambda item: (item.path, item.redaction_type))
        ],
        "limitations": limitations,
        "guardrails": list(guardrails),
    }
    content_hash = canonical_hash(stable_payload)
    generated_at = request.generated_at_or_as_of or utcnow(request.clock).isoformat()

    return ContextPackage(
        schema_version=CONTEXT_PACKAGE_SCHEMA,
        package_id=f"pkg_{content_hash[:24]}",
        generated_at_or_as_of=generated_at,
        target_scope=target_scope,
        source_priority=request.source_priority.ordered_sources,
        required_reads=required_reads_tuple,
        artifacts=artifacts,
        ranked_context=MappingProxyType(dict(ranked_context)) if ranked_context is not None else None,
        evidence_refs=evidence_refs,
        decision_refs=decision_refs,
        redaction_summary=tuple(sorted(redaction_records, key=lambda item: (item.path, item.redaction_type))),
        limitations=tuple(limitations),
        guardrails=guardrails,
        content_hash=content_hash,
    )
