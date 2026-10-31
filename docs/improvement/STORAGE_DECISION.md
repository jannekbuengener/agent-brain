# Improvement Blackboard Storage Decision — #48

**Issue:** [#48](https://github.com/jannekbuengener/agent-brain/issues/48)  
**Capability gate:** `reuse_before_build` (`DISCOVERY_REQUIRED`)

## Discovery order (evidence)

1. **Existing repository primitives** — `#47` `ImprovementObservationStore` port + `InMemoryImprovementObservationStore` fixture adapter. Reuse the port; do not invent a second write API.
2. **Existing repository dependencies** — Agent Brain runtime dependencies remain **none**. No accepted DB client package is already in-tree for production writes.
3. **Established libraries** — SQLite via **stdlib `sqlite3`** (no new dependency). Alternatives (Postgres, dedicated event-store packages) expand the dependency/ops surface without V1 need.
4. **Maintained OSS** — SurrealDB is researched for `#38/#10` read runtimes; not selected here.
5. **Workforce capabilities** — none supply durable Improvement storage.
6. **Official/upstream** — Python `sqlite3` is the stdlib persistence primitive for single-file, transactional local stores.
7. **Custom** — only a thin adapter behind the existing port.

## Rejected / deferred

| Option | Verdict | Why |
|---|---|---|
| SurrealDB (`#38/#10`) | DEFER | Planned around Knowledge/Memory read paths; must not become a backdoor into `#39` read-only stores or blur domain boundaries. |
| Pure JSONL files | REJECT for V1 concurrency | Weaker multi-writer transactional guarantees than SQLite for the pilot's parallel-agent requirement. |
| New SaaS / remote DB package | REJECT | Unnecessary dependency and ops surface before pilot evidence. |
| Mutating KnowledgeStore/MemoryStore | FORBIDDEN | Explicit non-goal of `#45/#47/#39`. |

## Decision

```text
Outcome: REUSE_EXISTING (ObservationStore port)
       + BUILD_CUSTOM thin adapter
       + ADOPT stdlib sqlite3 (no new package dependency)
```

Durable adapter: `SqliteImprovementObservationStore`  
Semantics must match the in-memory contract tests: append-only, idempotent, derived recurrence, fail-closed unavailable/identity errors, no management mutation surface.

## V1 scope note

Single-process / shared-file SQLite is sufficient for the cross-repo pilot hosts that can share a file path. Multi-region distributed writers remain out of scope until evidence requires it.
