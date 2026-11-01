"""Load #40 fixture / query / gold corpora with content hashes."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

FIXTURE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "benchmark"
    / "agent_memory_issue40"
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.name} must be a JSON object")
    return data, _sha256_bytes(raw)


@lru_cache(maxsize=1)
def load_fixtures() -> tuple[dict[str, Any], str]:
    return _load_json(FIXTURE_ROOT / "fixtures.v1.json")


@lru_cache(maxsize=1)
def load_queries() -> tuple[dict[str, Any], str]:
    return _load_json(FIXTURE_ROOT / "queries.v1.json")


@lru_cache(maxsize=1)
def load_gold() -> tuple[dict[str, Any], str]:
    return _load_json(FIXTURE_ROOT / "gold.v1.json")


def all_records() -> list[dict[str, Any]]:
    fixtures, _ = load_fixtures()
    records: list[dict[str, Any]] = []
    for fixture in fixtures["fixtures"]:
        for record in fixture["records"]:
            enriched = dict(record)
            enriched["fixture_id"] = fixture["fixture_id"]
            enriched["category"] = fixture["category"]
            records.append(enriched)
    return records


def gold_by_query() -> dict[str, dict[str, Any]]:
    gold, _ = load_gold()
    return {case["query_id"]: case for case in gold["cases"]}
