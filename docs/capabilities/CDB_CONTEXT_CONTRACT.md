# `cdb_context` Capability Contract

**Parent:** [#73](https://github.com/jannekbuengener/agent-brain/issues/73)  
**Schema:** `agent-brain-cdb-context-capability/v1`  
**Produkt:** Agent Brain  
**Capability:** `cdb_context`

## Pflicht-Capabilities

| Host-facing Name | Backend | Bestehende Surface |
|---|---|---|
| `agent_brain.health` | Protocol `health` | #12 |
| `cdb_context.briefing` | Protocol `context_read` (mode=briefing) | #12 / #6 |
| `cdb_context.search` | Protocol `retrieval` | #12 / #7 |
| `cdb_context.required_reads` | Domain `resolve_required_reads` + CDB `RequiredReadsProfile` | #6 |
| `cdb_context.evidence` | Protocol `evidence` | #12 / #8 |

Optionale Namen (`decision_history`, `impact`) sind in Goal 1 **nicht** exponiert und liefern `capability_unavailable`.

## Source- / Authority-Grenzen

1. Claire Repo Live / GitHub Live bleiben oberste Wahrheit für CDB.
2. Agent Brain liefert Context / Retrieval / Evidence — keine Trading-/Live-Autorität.
3. CDB-Spezifik liegt nur im Profil (`agent_brain.capabilities.cdb_context`).
4. Generischer Core importiert das CDB-Profil nicht.
5. Claire ist in diesem Contract `READ-ONLY EVIDENCE / SOURCE`.

Repository-Identity des Profils: `jannekbuengener/Claire_de_Binare`.

## Required Reads

- Engine: bestehende `RequiredReadsProfile` / `resolve_required_reads`
- Profil definiert nur CDB-Policy/Regeln auf kanonische Claire-Pfade
- keine statische Vollkopie des Claire-Canons als Plugin-Truth
- irrelevante Tasks erzeugen keine künstliche Voll-Ladung

## Live-Revalidation / Freshness

Keine zweite Status-Taxonomie. Kanonisch:

- `ResolutionState`: `CURRENT` / `STALE` / `SUPERSEDED` / `UNKNOWN`
- Response-`limitations`: u. a. `partial_source_state`, `source_unavailable`, `no_evidence`
- Live-/GitHub-/Repo-Quellen schlagen persistierten Context (`prefer_live_over_persisted`)

Invarianten:

- `UNAVAILABLE != EMPTY`
- `STALE != CURRENT`
- `NO_EVIDENCE != CONFIRMED`

## Failure Semantics

Wiederverwendet `ProtocolErrorCode` aus #12:

- `invalid_input`
- `invalid_scope`
- `capability_unavailable`
- `backend_unavailable`
- `contract_version_mismatch`
- `unsupported_operation` (Write-Boundary)
- `internal_failure`

Unterstützte Contract-Version → PASS. Inkompatible Version → expliziter Fehler. Kein stilles Downgrade.

## Evidence / Provenance

Capability-Antworten tragen vorhandene Source-/Evidence-Strukturen weiter (Briefing-, Retrieval-, Trust-Payloads). Hosts dürfen Evidence nicht aus bloßer Textausgabe rekonstruieren müssen. Fehlende Evidence wird als `NO_EVIDENCE` / `confirmed=false` markiert.

## Read-only Boundary

Nicht exponiert: Shell, generisches Filesystem, GitHub-Mutationen, DB-Admin, Trading-/Risk-/Live-Controls, `remember` / `consolidate` / generisches Write. Die #12-Write-Boundary wird wiederverwendet.

## Contract Versioning

- Capability-Schema: `agent-brain-cdb-context-capability/v1`
- Package-Version: #17 Source of Truth
- Beide Felder erscheinen in Contract-/Descriptor-Metadaten

## Adapter Responsibilities

Host-Adapter dürfen:

- Packaging / Registration
- Transport-Bindung an die hostneutralen Descriptors
- Host-UX / Rendering

Host-Adapter dürfen nicht:

- eigene Context-/Evidence-Semantik erfinden
- Capability-Definitionen pro Host forken
- Contract-Version still herabstufen

## Shared Host Contract Fixture

`tests/capabilities/test_host_contract_suite.py` — von späteren Host-Adaptern wiederverwendbar (`run_host_contract_suite`).

## Goal-2 Readiness Signal

Nach Goal-1 Foundation (dieses Dokument + Suite + Descriptors):

```text
LOCAL_HOST_SURFACES_READY: YES
```

bedeutet: Claude Code / Cursor / OpenCode Adapter können gebaut werden, ohne neue fachliche Capability-Entscheidungen treffen zu müssen (Contract, Descriptors, Version, Fixture, Failures, Profil stabil). ChatGPT remote packaging bleibt ein späteres Delivery-Goal unter #73.
