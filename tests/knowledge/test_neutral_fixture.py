"""Neutral knowledge snapshot fixture test (Slice 6, T6)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from agent_brain.connectors import build_repository_index
from agent_brain.connectors.ingestion import IngestionPolicy
from agent_brain.contracts import RepositoryProfile
from agent_brain.core.time import FixedClock
from agent_brain.knowledge.builder import build_knowledge_snapshot
from agent_brain.knowledge.serialization import serialize_knowledge_snapshot

TESTS_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = TESTS_ROOT / "fixtures" / "connectors" / "repository_neutral"
PROFILE_PATH = (
    TESTS_ROOT
    / "fixtures"
    / "connectors"
    / "repository_ingestion_profile.neutral.v1.json"
)
SNAPSHOT_PATH = TESTS_ROOT / "fixtures" / "knowledge" / "knowledge_snapshot.neutral.v1.json"

FIXED_TIME = datetime(2026, 1, 1, 12, 0, 0)


def test_neutral_fixture_is_canonical_snapshot() -> None:
    payload = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile = RepositoryProfile.from_dict(payload)
    ingestion = build_repository_index(FIXTURE_ROOT, profile, IngestionPolicy())
    snapshot = build_knowledge_snapshot(ingestion, clock=FixedClock(FIXED_TIME))
    assert serialize_knowledge_snapshot(snapshot) == SNAPSHOT_PATH.read_text(
        encoding="utf-8"
    )
