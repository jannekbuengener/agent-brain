# Meta-Goal #96 Acceptance Matrix

**Exit token:** `AGENT_BRAIN_SHARED_MEMORY_MULTI_REPO_OPERATIONAL`  
**Package:** `agent-brain==0.3.5` / `v0.3.5`  
**Provider main (pre-tag baseline):** track after G6 merge

## Gate evidence

| Gate | Status | Evidence |
| --- | --- | --- |
| G0 | PASS | [#96 checkpoint](https://github.com/jannekbuengener/agent-brain/issues/96#issuecomment-6612249819) |
| G1 | PASS | PR [#100](https://github.com/jannekbuengener/agent-brain/pull/100) → `8ff8918`; child #97 closed |
| G2 | PASS | PR [#101](https://github.com/jannekbuengener/agent-brain/pull/101) → `e0ab6c6`; child #98 closed |
| G3 | PASS | Harness PR [#102](https://github.com/jannekbuengener/agent-brain/pull/102); sample-brain [#1365](https://github.com/jannekbuengener/sample-brain/pull/1365); security-business [#35](https://github.com/jannekbuengener/security-business/pull/35); live [G3_CROSS_HOST_EVIDENCE.json](G3_CROSS_HOST_EVIDENCE.json) |
| G4 | PASS | workforce PR [#101](https://github.com/jannekbuengener/agent-workforce/pull/101) → `a1ed1ad`; child #100 closed |
| G5 | PASS | PR [#103](https://github.com/jannekbuengener/agent-brain/pull/103); [G5_REVOKE_RESTORE_EVIDENCE.json](G5_REVOKE_RESTORE_EVIDENCE.json); unit revoke-survives-restore |
| G6 | PASS | Release [v0.3.5](https://github.com/jannekbuengener/agent-brain/releases/tag/v0.3.5) on main `21cbabf`; host manifests synced; consumer pin PRs |

## Parent acceptance checklist

| Criterion | Evidence |
| --- | --- |
| Isolated Agent Brain SurrealDB; CDB untouched | compose `shared-memory.yml`; #94 restore proof; no CDB volume mutation in #96 PRs |
| Auth contract; no DB root to consumers | [SHARED_MEMORY_AUTH.md](SHARED_MEMORY_AUTH.md); `HandoffGateway`; MCP env token only |
| Two external consumers with grants/CI/main | sample-brain + security-business PRs merged |
| Two hosts: A stores, B new session uses | Cursor→Claude MCP sessions in G3 evidence + unit `test_g3_cross_host_session.py` |
| Cross-tenant denial | G3 evidence `cross_tenant_denied: true` |
| Idempotency / negatives | `tests/memory/test_handoff*.py`, `test_handoff_auth.py` |
| cdb_context / read-only ports unchanged | `test_readonly_tool_catalogue_unchanged` |
| Revoke survives restore | G5 evidence + denylist outside Surreal volume |
| Workforce discovery | `shared_memory_handoff` in REGISTRY + routing |
| Version pin | `agent-brain==0.3.5` / `v0.3.5` after G6 tag |

## Explicit HOLDs (not blockers for localhost multi-repo ops)

- Remote/public Surreal or MCP bind without Owner security approval.
- Full offsite encrypted backup of secrets+volume beyond local F: / secrets-dir denylist model.
- CDB product consumer adoption (deferred readiness).
