"""Portable, in-memory event normalization with fail-closed integrity checks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from agent_brain.contracts import ArtifactRef, IndexRecord
from agent_brain.core.canonical import canonical_hash
from agent_brain.core.redaction import redact_sensitive_mapping, redact_sensitive_text

_INTEGRITY_FIELDS = frozenset({"event_hash", "hash", "sha256", "signature", "event_signature"})


@dataclass(frozen=True, slots=True)
class LedgerIntegrityError(ValueError):
    """A batch-level integrity rejection that deliberately yields no records."""

    code: str
    reason: str
    event_ids: tuple[str, ...] = ()

    def __str__(self) -> str:
        return f"{self.code}: {self.reason}"


def _payload_for_hash(event: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in event.items() if key not in _INTEGRITY_FIELDS}


def _event_id(event: Mapping[str, object]) -> str:
    value = event.get("event_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return f"event-{canonical_hash(_payload_for_hash(event))}"


def _required_text(event: Mapping[str, object], field_name: str, event_id: str) -> str:
    value = event.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise LedgerIntegrityError(
            "event_invalid",
            f"{field_name} must be a non-blank string",
            (event_id,),
        )
    return value.strip()


def _declared_hash(event: Mapping[str, object]) -> tuple[str | None, str | None]:
    for field_name in ("event_hash", "hash", "sha256"):
        if field_name not in event:
            continue
        value = event[field_name]
        if not isinstance(value, str) or not value.strip():
            return field_name, ""
        return field_name, value.strip().lower().removeprefix("sha256:")
    return None, None


def _validate_integrity(event: Mapping[str, object], event_id: str) -> str:
    _required_text(event, "timestamp", event_id)
    _required_text(event, "agent_id", event_id)
    _, declared_hash = _declared_hash(event)
    payload_hash = canonical_hash(_payload_for_hash(event))
    if declared_hash is not None and declared_hash != payload_hash:
        raise LedgerIntegrityError("hash_mismatch", "declared hash does not match payload", (event_id,))
    for field_name in ("signature", "event_signature"):
        if field_name not in event:
            continue
        value = event[field_name]
        if not isinstance(value, str) or not value.strip():
            raise LedgerIntegrityError("signature_invalid", "signature is empty or malformed", (event_id,))
        raise LedgerIntegrityError(
            "signature_unsupported",
            "signature is present but no verifier is configured",
            (event_id,),
        )
    return payload_hash


def _redacted_event_attributes(event: Mapping[str, object]) -> dict[str, object]:
    data = {key: value for key, value in _payload_for_hash(event).items() if key != "evidence"}
    redacted = redact_sensitive_mapping(data)
    evidence = event.get("evidence", ())
    if isinstance(evidence, str):
        redacted["evidence"] = (redact_sensitive_text(evidence),)
    elif isinstance(evidence, Sequence) and not isinstance(evidence, (bytes, bytearray, str)):
        redacted["evidence"] = tuple(
            redact_sensitive_text(item) if isinstance(item, str) else redact_sensitive_mapping(item)
            for item in evidence
        )
    return redacted


def normalize_ledger_events(
    events: Sequence[Mapping[str, object]], *, source: ArtifactRef
) -> tuple[IndexRecord, ...]:
    """Validate an entire caller-supplied batch before producing shared index records."""
    if not isinstance(source, ArtifactRef):
        raise TypeError("source must be an ArtifactRef")
    normalized: list[tuple[str, str, str, Mapping[str, object], str]] = []
    for raw_event in events:
        if not isinstance(raw_event, Mapping):
            raise LedgerIntegrityError("event_invalid", "event must be a mapping")
        event = dict(raw_event)
        event_id = _event_id(event)
        payload_hash = _validate_integrity(event, event_id)
        timestamp = _required_text(event, "timestamp", event_id)
        agent_id = _required_text(event, "agent_id", event_id)
        normalized.append((timestamp, event_id, agent_id, event, payload_hash))

    agent_previous: dict[str, str] = {}
    records: list[IndexRecord] = []
    for timestamp, event_id, agent_id, event, payload_hash in sorted(
        normalized, key=lambda item: (item[0], item[1])
    ):
        attributes: dict[str, Any] = _redacted_event_attributes(event)
        attributes.update(
            {
                "event_id": event_id,
                "timestamp": timestamp,
                "agent_id": agent_id,
                "prev_event_id": agent_previous.get(agent_id),
            }
        )
        records.append(
            IndexRecord(
                schema_version="index-record/v1",
                record_id=f"record-{canonical_hash({'source': source.artifact_id, 'event_id': event_id})}",
                record_type="ledger_event",
                source=source,
                content_hash=payload_hash,
                attributes=attributes,
            )
        )
        agent_previous[agent_id] = event_id
    return tuple(records)
