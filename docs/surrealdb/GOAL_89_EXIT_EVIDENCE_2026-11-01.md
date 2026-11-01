# Goal #89 Exit Evidence — 2026-11-01

**Goal:** #89 — `SURREAL_DURABLE_IMPROVEMENT_PERSISTENCE_GO`  
**Implementation owner:** #64 — `SURREAL_IMPROVEMENT_STORE_OPERATIONAL`  
**Parent Meta:** #65 — `SURREALDB_AGENT_BRAIN_FOUNDATION_OPERATIONAL`

```text
#64 CLOSED != GOAL PASS
DB CONNECTED != GOAL PASS
WRITES SUCCEED != GOAL PASS
CHILDREN CLOSED != META PASS
```

## Authority

```text
NO_NEW_AUTHORITY
EXECUTE_EXISTING_#89
COORDINATE_EXISTING_#64
PARENT_#65_REMAINS_META_OWNER
UPDATE_EXISTING / EXECUTE_EXISTING
```

Consumed closed foundation evidence: #38, #39, #10, #21, #67.  
Improvement domain authorities unchanged: #45–#52.  
#40 Agent Memory remains independent / not adopted.

## Runtime

| Field | Evidence | Classification |
|---|---|---|
| SurrealDB version | HTTP `/version` → `surrealdb-3.0.4` | `VERIFIED` |
| Image digest | `surrealdb/surrealdb@sha256:65000ff205b08363b035b457f292dc0a0b1cd4212935dd5ea94073cf67adf306` | `PINNED` (same as #38) |
| Storage engine (acceptance scratch) | `memory` disposable container `agent_brain_89_surreal_scratch` | `VERIFIED_TEST_RUNTIME` |
| Storage engine (#38 baseline) | SurrealKV on isolated scratch volume (not mutated here) | `REUSED_EVIDENCE` |
| Namespace | `agent_brain_89` (tests allocate unique DBs under this NS) | `VERIFIED` |
| Database | per-test `imp_<uuid>` / `restore_<uuid>` | `VERIFIED_ISOLATED` |
| Schema | `improvement-surreal/v1` tables `improvement`, `improvement_observation` | `VERIFIED` |
| Indexes | `improvement_id_unique`, `observation_id_unique`, `observation_idempotency_unique`, `observation_by_improvement` | `VERIFIED` |
| Connection mode | HTTP `/sql` + `/version`, stdlib urllib, no Surreal SDK | `VERIFIED` |
| Unknown datastore start | Claire volume `cdb_database_surrealdb_data` **not** attached | `PASS` |

Config vs runtime: endpoint/NS/DB settings are structural; availability and version are probed at runtime. `UNAVAILABLE` is never treated as empty/safe-to-write.

## Store

| Gate | Result | Evidence |
|---|---|---|
| Adapter | `SurrealImprovementObservationStore` behind `ImprovementObservationStore` | `src/agent_brain/improvement/surreal.py` |
| Contract parity | PASS | `tests/improvement/test_surreal_store_live.py` |
| Append-only | PASS | observations inserted only; no overwrite API |
| Idempotency | PASS | same `idempotency_key` / retry → single event |
| Parallel writers | PASS | 20 concurrent writers + per-writer retry |
| Retry safety | PASS | parallel suite retries each event |
| Aggregate rebuild | PASS | `_refresh_aggregate` derives recurrence/lifecycle |
| Projection | PASS | existing `#51` Markdown projection against Surreal store |
| Management / revision | PASS | `SurrealImprovementManagementPort` stale revision rejected |
| SQLite retained | PASS | `SqliteImprovementObservationStore` unchanged |
| InMemory retained | PASS | unchanged |

## Recovery

| Gate | Result | Evidence |
|---|---|---|
| Backup/Export | PASS | `export_board_snapshot()` → canonical JSON + SHA-256 |
| Restore target | PASS | isolated empty Surreal DB (`restore_<uuid>`) |
| Restore | PASS | `import_board_snapshot()` |
| Post-restore parity | PASS | same observation ids, identity, recurrence |
| Event loss | `0` | parallel→backup→restore suite |
| Duplicate events | `0` | idempotent retry under parallel load |
| Non-empty import | fail-closed | refuses overwrite of destination |

## Boundaries

| Gate | Result |
|---|---|
| KnowledgeStore read-only | PASS (`assert_read_only_store` / no write methods) |
| MemoryStore read-only | PASS |
| Typed Improvement writes only | PASS |
| Generic write surface | NONE |
| Agent Memory adoption (#40) | NONE |
| GitHub execution truth | PRESERVED (work_refs only) |
| Secret safety | PASS (no credentials in evidence/export runtime block) |

## Failure / reconnect

| Gate | Result |
|---|---|
| Endpoint unavailable | `ImprovementStoreUnavailable` |
| Version mismatch | `ImprovementStoreUnavailable` |
| Mark unavailable after use | list/submit raise; never empty board |
| Schema bootstrap failure | fail-closed unavailable |

## Validation commands

```bash
python -m ruff check .
python -m pytest -q tests/improvement tests/surrealdb
python -m pytest -q
```

Live Surreal endpoint (isolated scratch only):

```bash
export AGENT_BRAIN_SURREAL_ENDPOINT=http://127.0.0.1:8010
```

## #65 Meta readiness (independent)

Reuses #38/#10/#21/#67 plus this Goal:

| Meta requirement | Status |
|---|---|
| Runtime safely identified / operational | PASS (3.0.4 pinned) |
| No unknown datastore semantics | PASS |
| Native read path operational | PASS (#10/#67) |
| Safe state handoff operational | PASS (#21/#67) |
| Durable improvement store operational | PASS (#64) |
| Backup/recovery proven | PASS (#89) |
| Failure degradation proven | PASS |
| Authority boundaries preserved | PASS |

Exit token when GitHub/repo live absorbs merge + issue closeout:

`SURREAL_DURABLE_IMPROVEMENT_PERSISTENCE_GO`

Meta exit when independently closed after this Goal:

`SURREALDB_AGENT_BRAIN_FOUNDATION_OPERATIONAL`
