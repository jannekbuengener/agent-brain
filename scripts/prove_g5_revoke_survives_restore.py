"""G5 evidence: revoked credentials stay denied after restoring an older grant snapshot."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from agent_brain.memory.handoff_auth import (
    HandoffCredentialStore,
    HandoffForbidden,
    HandoffOperation,
    RevokeDenylist,
    load_or_create_pepper,
)


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="g5-restore-"))
    try:
        sandbox = root / "secrets"
        sandbox.mkdir()
        store = HandoffCredentialStore(
            pepper=load_or_create_pepper(sandbox),
            denylist=RevokeDenylist(sandbox / "handoff_revoke_denylist.jsonl"),
            grants_path=sandbox / "handoff_grants.json",
        )
        grant, token = store.enroll(
            consumer_id="g5-drill",
            repository_ref="jannekbuengener/sample-brain",
            operations=[HandoffOperation.APPEND, HandoffOperation.RECALL],
        )
        backup = store.export_grants_snapshot()
        store.revoke(grant.grant_id, reason="g5-drill")
        store.restore_grants_snapshot(backup)
        denied = False
        try:
            store.authenticate(
                token,
                repository_ref="jannekbuengener/sample-brain",
                operation=HandoffOperation.RECALL,
            )
        except HandoffForbidden:
            denied = True
        evidence = {
            "ok": denied,
            "gate": "G5_REVOKE_SURVIVES_GRANT_RESTORE",
            "grant_status_after_restore": next(
                g.status for g in store.list_grants() if g.grant_id == grant.grant_id
            ),
            "denylist_path_outside_volume": (
                "AGENT_BRAIN_SECRETS_PATH/handoff_revoke_denylist.jsonl"
            ),
        }
        out = Path("docs/operations/G5_REVOKE_RESTORE_EVIDENCE.json")
        out.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(evidence, ensure_ascii=False))
        return 0 if denied else 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
