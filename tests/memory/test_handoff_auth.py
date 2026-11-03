"""G1 AuthN/AuthZ contract and revoke-survives-restore invariant."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_brain.memory.handoff import HandoffEvent, SurrealHandoffJournal
from agent_brain.memory.handoff_auth import (
    HandoffCredentialStore,
    HandoffForbidden,
    HandoffOperation,
    RevokeDenylist,
    hash_consumer_token,
    load_or_create_pepper,
    mint_consumer_token,
)
from agent_brain.memory.handoff_gateway import HandoffGateway
from agent_brain.surrealdb.http import SurrealHttpProbeResult


def _store(tmp_path: Path) -> HandoffCredentialStore:
    pepper = load_or_create_pepper(tmp_path)
    denylist = RevokeDenylist(tmp_path / "handoff_revoke_denylist.jsonl")
    return HandoffCredentialStore(
        pepper=pepper,
        denylist=denylist,
        grants_path=tmp_path / "handoff_grants.json",
    )


def test_enroll_stores_hash_not_plaintext(tmp_path: Path) -> None:
    store = _store(tmp_path)
    grant, token = store.enroll(
        consumer_id="sample-brain",
        repository_ref="jannekbuengener/sample-brain",
        operations=[HandoffOperation.APPEND, HandoffOperation.RECALL],
    )
    snapshot = store.export_grants_snapshot()
    blob = str(snapshot)
    assert token not in blob
    assert grant.token_hash in blob
    assert hash_consumer_token(token, pepper=load_or_create_pepper(tmp_path)) == grant.token_hash
    listed = store.list_grants()[0].to_public_dict()
    assert "token_hash" not in listed
    assert listed["repository_ref"] == "jannekbuengener/sample-brain"


def test_cross_repo_spoof_and_missing_op_denied(tmp_path: Path) -> None:
    store = _store(tmp_path)
    grant, token = store.enroll(
        consumer_id="sample-brain",
        repository_ref="jannekbuengener/sample-brain",
        operations=[HandoffOperation.RECALL],
    )
    del grant
    with pytest.raises(HandoffForbidden, match="repository grant denied"):
        store.authenticate(
            token,
            repository_ref="jannekbuengener/security-business",
            operation=HandoffOperation.RECALL,
        )
    with pytest.raises(HandoffForbidden, match="operation grant denied"):
        store.authenticate(
            token,
            repository_ref="jannekbuengener/sample-brain",
            operation=HandoffOperation.APPEND,
        )


def test_bad_token_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.enroll(
        consumer_id="dogfood",
        repository_ref="jannekbuengener/agent-brain",
        operations=[HandoffOperation.APPEND],
    )
    with pytest.raises(HandoffForbidden):
        store.authenticate(
            mint_consumer_token(),
            repository_ref="jannekbuengener/agent-brain",
            operation=HandoffOperation.APPEND,
        )


def test_rotate_revokes_previous_token(tmp_path: Path) -> None:
    store = _store(tmp_path)
    grant, old_token = store.enroll(
        consumer_id="dogfood",
        repository_ref="jannekbuengener/agent-brain",
        operations=[HandoffOperation.APPEND, HandoffOperation.RECALL],
    )
    new_grant, new_token = store.rotate(grant.grant_id)
    assert new_grant.rotated_from == grant.grant_id
    with pytest.raises(HandoffForbidden, match="revoked"):
        store.authenticate(
            old_token,
            repository_ref="jannekbuengener/agent-brain",
            operation=HandoffOperation.RECALL,
        )
    ctx = store.authenticate(
        new_token,
        repository_ref="jannekbuengener/agent-brain",
        operation=HandoffOperation.RECALL,
    )
    assert ctx.grant_id == new_grant.grant_id


def test_revoked_credential_not_revived_by_grant_snapshot_restore(tmp_path: Path) -> None:
    """G1/G5 invariant: denylist outside backup prevents revive-on-restore."""
    store = _store(tmp_path)
    grant, token = store.enroll(
        consumer_id="sample-brain",
        repository_ref="jannekbuengener/sample-brain",
        operations=[HandoffOperation.APPEND, HandoffOperation.RECALL],
    )
    old_snapshot = store.export_grants_snapshot()
    store.revoke(grant.grant_id, reason="compromised")
    with pytest.raises(HandoffForbidden, match="revoked"):
        store.authenticate(
            token,
            repository_ref="jannekbuengener/sample-brain",
            operation=HandoffOperation.RECALL,
        )

    # Simulate restoring an older grant registry / DB backup that still marks
    # the credential active. The external denylist must keep it dead.
    store.restore_grants_snapshot(old_snapshot)
    restored = next(g for g in store.list_grants() if g.grant_id == grant.grant_id)
    assert restored.status == "active"
    with pytest.raises(HandoffForbidden, match="revoked"):
        store.authenticate(
            token,
            repository_ref="jannekbuengener/sample-brain",
            operation=HandoffOperation.RECALL,
        )


class _MemoryJournal:
    """Minimal journal stand-in for gateway unit tests."""

    def __init__(self) -> None:
        self.events: list[HandoffEvent] = []

    def append(self, **kwargs: str) -> HandoffEvent:
        event = HandoffEvent(
            event_key="k1",
            repository_ref=kwargs["repository_ref"],
            agent_id=kwargs["agent_id"],
            task_ref=kwargs["task_ref"],
            status=kwargs["status"],
            summary=kwargs["summary"],
            next_step=kwargs["next_step"],
            source_ref=kwargs["source_ref"],
            created_at="2026-11-03T00:00:00.000000Z",
        )
        self.events.append(event)
        return event

    def recall(self, *, repository_ref: str, task_ref: str | None = None, limit: int = 20):
        del limit
        return [
            event
            for event in self.events
            if event.repository_ref == repository_ref
            and (task_ref is None or event.task_ref == task_ref)
        ]


def test_gateway_binds_auth_repo_not_payload_spoof(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _, token_a = store.enroll(
        consumer_id="sample-brain",
        repository_ref="jannekbuengener/sample-brain",
        operations=[HandoffOperation.APPEND, HandoffOperation.RECALL],
    )
    _, token_b = store.enroll(
        consumer_id="security-business",
        repository_ref="jannekbuengener/security-business",
        operations=[HandoffOperation.APPEND, HandoffOperation.RECALL],
    )
    journal: SurrealHandoffJournal = _MemoryJournal()  # type: ignore[assignment]
    gateway = HandoffGateway(store, journal)
    denied = gateway.append(
        token_a,
        {
            "repository_ref": "jannekbuengener/security-business",
            "agent_id": "cursor",
            "task_ref": "issue:1",
            "status": "in_progress",
            "summary": "spoof attempt",
            "next_step": "should fail",
            "source_ref": "test",
            "idempotency_key": "spoof-1",
        },
    )
    assert denied.ok is False
    assert denied.code == "FORBIDDEN"

    ok = gateway.append(
        token_a,
        {
            "repository_ref": "jannekbuengener/sample-brain",
            "agent_id": "cursor",
            "task_ref": "issue:1",
            "status": "in_progress",
            "summary": "real work",
            "next_step": "continue",
            "source_ref": "test",
            "idempotency_key": "ok-1",
        },
    )
    assert ok.ok is True
    foreign = gateway.recall(token_b, repository_ref="jannekbuengener/sample-brain")
    assert foreign.ok is False
    assert foreign.code == "FORBIDDEN"


def test_surreal_journal_type_still_importable() -> None:
    # Keep gateway typing aligned with the real journal without requiring live DB.
    assert SurrealHandoffJournal is not None
    assert SurrealHttpProbeResult is not None
