"""Opt-in real SurrealDB handoff acceptance on isolated test namespace.

Run only with AGENT_BRAIN_HANDOFF_LIVE=1 on the dedicated 8012 endpoint.
No CDB volume, no external Memory API, no production shared_memory DB.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

from agent_brain.memory.handoff import (
    HandoffConflict,
    SurrealHandoffJournal,
    load_local_authorization,
)
from agent_brain.surrealdb.config import SurrealDbReadSettings

pytestmark = pytest.mark.skipif(
    os.environ.get("AGENT_BRAIN_HANDOFF_LIVE") != "1",
    reason="explicit isolated Agent Brain runtime required",
)


def test_live_two_agent_handoff_idempotency_and_repo_isolation() -> None:
    settings = SurrealDbReadSettings(
        endpoint="http://127.0.0.1:8012",
        namespace="agent_brain_acceptance",
        database="handoff",
        timeout_seconds=5.0,
        expected_server_version_prefix="surrealdb-3.0",
    )
    auth = load_local_authorization()
    first = SurrealHandoffJournal(settings, authorization=auth)
    task = "smoke:" + uuid4().hex
    record = {
        "repository_ref": "jannekbuengener/agent-brain",
        "agent_id": "claude-code",
        "task_ref": task,
        "status": "in_progress",
        "summary": "Agent A: work unfinished; schema ready",
        "next_step": "Agent B should verify integration",
        "source_ref": "repo:docs/operations/SHARED_MEMORY.md",
        "idempotency_key": task + ":first",
    }
    saved = first.append(**record)
    other_process = SurrealHandoffJournal(settings, authorization=auth)
    assert other_process.append(**record) == saved
    assert other_process.recall(repository_ref=record["repository_ref"], task_ref=task) == [saved]
    assert (
        other_process.recall(repository_ref="jannekbuengener/Claire_de_Binare", task_ref=task) == []
    )
    with pytest.raises(HandoffConflict):
        other_process.append(**(record | {"summary": "changed"}))
    second = other_process.append(
        **(
            record
            | {
                "agent_id": "codex",
                "status": "completed",
                "summary": "Agent B: integration verified",
                "next_step": "Close after CI",
                "idempotency_key": task + ":second",
            }
        )
    )
    assert second.event_key != saved.event_key
    assert len(first.recall(repository_ref=record["repository_ref"], task_ref=task)) == 2
