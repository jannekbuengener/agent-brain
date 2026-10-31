# State-Handoff Decision — 2026-10-31

**Issues:** #21 (authority), #38 (evidence), #67 (delivery goal)  
**Code:** `agent_brain.surrealdb.handoff.issue_38_scratch_handoff_decision_2026_10_31`

## Consumed #38 evidence

- Server 3.0.4 on scratch against digest-pinned image
- Volume `cdb_database_surrealdb_data` / SurrealKV
- Configured NS `cdb_context_local` **ABSENT**
- Canonical #21 classes **ABSENT** (tables missing)
- Only Issue-639 governance mirror seeds present (not #21 primary classes)
- VERSION unsupported on datastore

## ELSEWHERE search (2026-10-31, same host)

| Candidate | Result |
|---|---|
| Docker volumes matching surreal/context/cdb_database | `cdb_database_surrealdb_data`, scratch clone, `claude-memory` |
| `claude-memory` RO listing | **not** SurrealKV (only `index.js`) |
| Claire host data dirs (`data/`, `var/`, `.surrealdb`, `infrastructure/data`) | **missing** |
| Compose mapping | Claire local SurrealKV → named volume `surrealdb_data` → `cdb_database_surrealdb_data` |
| Configured NS `cdb_context_local` on that volume | **ABSENT** (never created) |
| Target productive layout `cdb`/`context_intelligence` | Claire docs: target contract, **not applied** |

Conclusion: on this workstation there is **no second Claire SurrealKV** holding Agent-Brain primary classes. The inventaried volume is the only compose-mapped candidate; canonical #21 classes are ABSENT there.

## Gate results

### Conservative helper (explicit unconfirmed)

`issue_38_scratch_handoff_decision_2026_10_31()` defaults to:

```text
outcome:           STATE_HANDOFF_BLOCKED
volume_authority:  unconfirmed
```

### Evidence-backed decision (ELSEWHERE search consumed)

`evidence_backed_handoff_2026_10_31()` / `local_runtime_truth_2026_10_31().handoff_decision()`:

```text
outcome:           STATE_HANDOFF_GO
volume_authority:  confirmed_primary
dispositions:      NOOP_ABSENT per canonical #21 class
```

Meaning: no SurrealDB-primary Memory/Evidence/Claim corpus to migrate on the
only local Claire SurrealKV candidate; reconstructible knowledge stays
`REBUILD_FROM_SOURCE` via #16, not a silent empty inventarization.

If later evidence shows another Surreal primary, authority must flip to
`elsewhere` and handoff returns **BLOCKED** until that store is inventarized.

## What this does not claim

- It does not close #21 or #67 by itself.
- It does not authorize Compose start of the original volume with floating `latest`.
- It does not migrate governance mirror drill seeds into Agent Brain memory.
