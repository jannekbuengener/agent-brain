# Shared Memory Consumer Auth (G1)

**Parent:** Agent Brain [#96](https://github.com/jannekbuengener/agent-brain/issues/96) · Child [#97](https://github.com/jannekbuengener/agent-brain/issues/97)  
**Contract:** `handoff-auth/v1` + gateway `shared-memory-handoff/v1`  
**Status:** Local provider AuthN/AuthZ foundation. Remote/public bind remains Owner-gated.

## Threat model (binding negatives)

| Attack | Control |
| --- | --- |
| Spoofed `repository_ref` in payload | Server authenticates token → grant.repository_ref; mismatch → `FORBIDDEN` |
| Free-form `agent_id` as identity | Never an AuthN trust anchor; audit-only |
| Stolen plaintext token in DB/backup | Only HMAC token hashes stored; pepper under secrets dir |
| Revoke then restore older Surreal/grant backup | Append-only revoke denylist **outside** Surreal volume; auth checks denylist first |
| Cross-tenant read/write | Per-repo least-privilege ops (`append`, `recall`) |
| Root Surreal credential to consumers | Forbidden; gateway holds DB Basic auth |

## Files under `AGENT_BRAIN_SECRETS_PATH`

| File | Purpose |
| --- | --- |
| `HANDOFF_TOKEN_PEPPER` | HMAC pepper (create-once, never commit) |
| `handoff_grants.json` | Grant registry with **token hashes only** |
| `handoff_revoke_denylist.jsonl` | Append-only revoke log; must survive Surreal volume restore |
| `SURREALDB_ENV` | Existing Surreal root (provider host only) |

## Operator commands

```text
agent-brain-handoff-auth enroll --consumer-id sample-brain --repository jannekbuengener/sample-brain --ops append,recall
agent-brain-handoff-auth rotate --grant-id grant_...
agent-brain-handoff-auth revoke --grant-id grant_... --reason compromised
agent-brain-handoff-auth list
```

Enroll/rotate print the plaintext token **once**. Store it in the consumer host secret store / MCP env (`AGENT_BRAIN_HANDOFF_TOKEN`). Never commit tokens.

## Restore vs revoke invariant

1. Enroll consumer → active grant hash in registry.
2. Take grant/DB backup snapshot.
3. Revoke → hash appended to denylist; auth fails.
4. Restore older grant/DB snapshot that still marks the grant active.
5. Auth with the old token must still fail because the denylist was not rolled back.

Unit coverage: `tests/memory/test_handoff_auth.py::test_revoked_credential_not_revived_by_grant_snapshot_restore`.  
Full volume drill: G5 / [#99](https://github.com/jannekbuengener/agent-brain/issues/99).

## Application API

`HandoffGateway` wraps `SurrealHandoffJournal` and returns structured results with codes `OK`, `EMPTY`, `FORBIDDEN`, `INVALID_REQUEST`.

## MCP binding (G2)

- Entry: `agent-brain-mcp-handoff` (reuses `McpStdioServer`; **no** second MCP SDK/runtime).
- Tools: `shared_memory.handoff.append`, `shared_memory.handoff.recall`.
- Host token env: `AGENT_BRAIN_HANDOFF_TOKEN` (Cursor/Claude snippets via `cursor_handoff_mcp_json` / `claude_code_handoff_mcp_json`).
- Existing `agent-brain-mcp` read-only `cdb_context` catalogue stays unchanged.
