# Improvement Observation Write Boundary — #47

**Status:** `OBSERVATION_WRITE_BOUNDARY_V1`  
**Issue:** [#47](https://github.com/jannekbuengener/agent-brain/issues/47)  
**Depends on:** [#46 contracts](https://github.com/jannekbuengener/agent-brain/issues/46)

## Zweck

Eng typisierter, append-only Write-Pfad für Skill-Improvement-Observations — getrennt von `KnowledgeStore` / `MemoryStore` (#39) und ohne Management-Mutationen (#52).

## Port

```text
ImprovementObservationStore
  submit_observation()   # idempotent append
  get_improvement()
  list_improvements()
  list_observations()
  find_candidates()      # exact/scoped lookup; no auto-merge
```

Adapters:

- `InMemoryImprovementObservationStore` — Fixture/Contract-Tests (#47)
- `SqliteImprovementObservationStore` — durable stdlib SQLite adapter (#48; see [`STORAGE_DECISION.md`](STORAGE_DECISION.md))

## Invarianten

1. Observation Writes sind append-only.
2. `idempotency_key` Retry → gleiches Resultat, kein zweites Event.
3. `recurrence` wird aus Observation-Count abgeleitet; bei `>= 2` und Lifecycle `NEW` → `RECURRING`.
4. Unklare Identity (`root_cause_key` und `improvement_id` fehlen) → `ImprovementIdentityAmbiguous`.
5. Observation Writer besitzt keine Management-Methoden (`set_priority`, `transition_lifecycle`, `merge_improvements`, Work-Item-/Verification-Links).
6. Unavailable Backend → `ImprovementStoreUnavailable`.

## Dedupe (#49)

`assess_observation()` / `merge_improvements()` / `relate_improvements()`:

- Exact `root_cause_key` → `EXACT_IDENTITY` (auto-attach allowed)
- Strong textual similarity → `POSSIBLE_DUPLICATE` (**no** auto-merge)
- Weak similarity → `RELATED` (**no** auto-merge)
- Merge requires explicit actor/reason/evidence lineage

## Management Port (#52)

`ImprovementManagementPort` / `InMemoryImprovementManagementPort`:

- `set_priority`, `transition_lifecycle`, `merge_improvements`
- `link_work_item`, `link_pull_request`, `record_verification`
- Actor must be `role=improvement-board-manager`
- Optimistic `expected_revision` conflicts fail closed
- ObservationStore still has none of these methods

## Protocol Surface (#50)

Capability-gated gateway (`ImprovementProtocolGateway`) + CLI (`python -m agent_brain.improvement.cli`):

- Observation tools require `improvement_observation_write` / reads require `improvement_read`
- Management tools default-deny unless `improvement_management_write`
- Host-neutral `tool_schemas()` — no MCP runtime dependency; Slice #12 stays untouched
- `capability_readback()` exposes READ / OBSERVATION_WRITE / MANAGEMENT_WRITE

## Non-goals

- keine Memory-/Knowledge-Write-Freigabe
- semantische Ähnlichkeit allein darf niemals auto-mergen
- keine GitHub Issue Create Authority in Agent Brain (Workforce #51)
- private ChatGPT-MCP is never a repo dependency
