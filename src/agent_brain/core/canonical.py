"""Canonical JSON serialization and deterministic SHA-256 helpers."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any


def _sanitize_float(value: Any) -> Any:
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        rounded = round(value, 10)
        if rounded == 0.0:
            rounded = 0.0
        return rounded
    if isinstance(value, dict):
        return {key: _sanitize_float(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_float(item) for item in value]
    return value


def _omit_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _omit_none(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_omit_none(item) for item in value]
    return value


def canonical_json_dumps(value: Any) -> str:
    """Return deterministic compact JSON with stable float and None handling."""
    sanitized = _sanitize_float(value)
    cleaned = _omit_none(sanitized)
    return json.dumps(cleaned, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def sha256_hex(data: bytes) -> str:
    """Return the lowercase SHA-256 digest for raw bytes."""
    return hashlib.sha256(data).hexdigest()


def canonical_hash(value: Any) -> str:
    """Hash the UTF-8 bytes of canonical JSON."""
    return sha256_hex(canonical_json_dumps(value).encode("utf-8"))
