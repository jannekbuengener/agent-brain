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

In-Memory Adapter: `InMemoryImprovementObservationStore` (Fixture/Contract-Tests). Persistenzwahl ist #48.

## Invarianten

1. Observation Writes sind append-only.
2. `idempotency_key` Retry → gleiches Resultat, kein zweites Event.
3. `recurrence` wird aus Observation-Count abgeleitet; bei `>= 2` und Lifecycle `NEW` → `RECURRING`.
4. Unklare Identity (`root_cause_key` und `improvement_id` fehlen) → `ImprovementIdentityAmbiguous`.
5. Observation Writer besitzt keine Management-Methoden (`set_priority`, `transition_lifecycle`, `merge_improvements`, Work-Item-/Verification-Links).
6. Unavailable Backend → `ImprovementStoreUnavailable`.

## Non-goals

- kein Storage-Backend (#48)
- kein Dedupe-Merge (#49)
- kein Management Port (#52)
- kein CLI/MCP (#50)
- keine Memory-/Knowledge-Write-Freigabe
