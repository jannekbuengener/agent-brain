"""Deterministic serialization helpers for shared contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_brain.core.canonical import canonical_json_dumps


def contract_payload(**fields: object) -> dict[str, object]:
    """Build a shallow payload while preserving explicit contract fields."""
    return dict(fields)


def serialize_contract(payload: Mapping[str, Any]) -> str:
    """Serialize a contract mapping using Agent Brain canonical JSON."""
    return canonical_json_dumps(dict(payload))
