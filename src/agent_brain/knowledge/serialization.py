"""Fail-closed serialization for Slice 6 knowledge snapshots."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from agent_brain.contracts.serialization import contract_payload, serialize_contract
from agent_brain.contracts.versioning import require_compatible_version
from agent_brain.knowledge.snapshot import (
    KNOWLEDGE_SNAPSHOT_SCHEMA,
    BuildMetadata,
    KnowledgeManifest,
    KnowledgeSnapshot,
)

_PAYLOAD_FIELDS = frozenset({"schema_version", "metadata", "manifests"})
_METADATA_FIELDS = frozenset({"built_at", "tool_version", "schema_version"})
_MANIFEST_FIELDS = frozenset({"source_ref", "source_hash"})


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return value


def _require_exact_fields(
    mapping: Mapping[str, Any],
    label: str,
    required_fields: frozenset[str],
) -> None:
    required = sorted(required_fields)
    missing = sorted(str(field) for field in required_fields if field not in mapping)
    if missing:
        raise ValueError(
            f"{label} missing required fields from {required}: {', '.join(missing)}"
        )
    unexpected = sorted(str(key) for key in mapping if key not in required_fields)
    if unexpected:
        raise ValueError(
            f"{label} contains unexpected fields: {', '.join(unexpected)}"
        )


def serialize_knowledge_snapshot(snapshot: KnowledgeSnapshot) -> str:
    """Serialize a knowledge snapshot to deterministic canonical JSON."""
    if not isinstance(snapshot, KnowledgeSnapshot):
        raise TypeError("snapshot must be a KnowledgeSnapshot")
    payload = contract_payload(
        schema_version=snapshot.schema_version,
        metadata=contract_payload(
            built_at=snapshot.metadata.built_at,
            tool_version=snapshot.metadata.tool_version,
            schema_version=snapshot.metadata.schema_version,
        ),
        manifests=[
            contract_payload(source_ref=manifest.source_ref, source_hash=manifest.source_hash)
            for manifest in snapshot.manifests
        ],
    )
    return serialize_contract(payload)


def parse_knowledge_snapshot(payload: str | Mapping[str, Any]) -> KnowledgeSnapshot:
    """Parse a snapshot payload (JSON string or mapping) fail-closed."""
    if isinstance(payload, str):
        try:
            document: Any = json.loads(payload)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid snapshot payload: not valid JSON ({error})") from error
    elif isinstance(payload, Mapping):
        document = payload
    else:
        raise TypeError("invalid snapshot payload: expected JSON string or mapping")

    document = _require_mapping(document, "snapshot payload")
    _require_exact_fields(document, "snapshot payload", _PAYLOAD_FIELDS)

    require_compatible_version(
        str(document["schema_version"]),
        expected_family="knowledge-snapshot",
        supported_major=1,
    )

    metadata_raw = _require_mapping(document["metadata"], "snapshot payload metadata")
    _require_exact_fields(
        metadata_raw,
        "snapshot payload metadata",
        _METADATA_FIELDS,
    )
    metadata = BuildMetadata(
        built_at=str(metadata_raw["built_at"]),
        tool_version=str(metadata_raw["tool_version"]),
        schema_version=str(metadata_raw["schema_version"]),
    )

    manifests_raw = document["manifests"]
    if isinstance(manifests_raw, (str, bytes)) or not isinstance(manifests_raw, Sequence):
        raise TypeError("snapshot payload manifests must be a sequence")

    manifests: list[KnowledgeManifest] = []
    for index, entry in enumerate(manifests_raw):
        entry_label = f"snapshot payload manifest entry {index}"
        entry_raw = _require_mapping(entry, entry_label)
        _require_exact_fields(entry_raw, entry_label, _MANIFEST_FIELDS)
        manifests.append(
            KnowledgeManifest(
                source_ref=str(entry_raw["source_ref"]),
                source_hash=str(entry_raw["source_hash"]),
            )
        )

    expected_schema = str(metadata.schema_version) if metadata.schema_version else KNOWLEDGE_SNAPSHOT_SCHEMA
    if expected_schema != str(document["schema_version"]):
        raise ValueError(
            "snapshot payload schema_version must match metadata.schema_version: "
            f"payload={document['schema_version']!r}, metadata={metadata.schema_version!r}"
        )

    return KnowledgeSnapshot(metadata=metadata, manifests=tuple(manifests))
