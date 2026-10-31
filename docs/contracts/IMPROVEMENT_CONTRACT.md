# Improvement Blackboard Contracts — #46

**Status:** `IMPROVEMENT_CONTRACTS_V1`  
**Issue:** [#46 — Improvement-/Observation-/Lifecycle-Verträge](https://github.com/jannekbuengener/agent-brain/issues/46)  
**Parent:** [#45 — Improvement Blackboard Epic](https://github.com/jannekbuengener/agent-brain/issues/45)

## Zweck

Backend-neutrale Domain-Verträge für das Skill-Improvement-Blackboard:

- `Improvement` = stabile Root-Cause-/Verbesserungs-Identität
- `ImprovementObservation` = einzelnes append-only Learning-/Evidence-Event
- Lifecycle, Merge-Lineage und Work-Refs ohne Storage-/Protocol-/GitHub-Authority

Diese Schicht ist **keine Runtime**. Sie schreibt weder `KnowledgeStore` noch `MemoryStore` und öffnet keine generischen `remember()`/`write()`-Pfade.

## Contract-Familien

| Familie | Schema | Zweck |
|---|---|---|
| `Improvement` | `improvement/v1` | stabile Improvement-Identität inkl. abgeleiteter `recurrence`-Projektion |
| `ImprovementObservation` | `improvement-observation/v1` | append-only Observation mit `idempotency_key` |
| `ImprovementMergeLineage` | `improvement-merge-lineage/v1` | auditierte Merge-Historie |
| `ImprovementWorkRef` | `improvement-work-ref/v1` | Zeiger auf GitHub Issue/PR/Verification (Execution Truth) |

Zusätzliche Enums/Relations:

- Lifecycle: `NEW | RECURRING | VALIDATED | PLANNED | IMPLEMENTED | VERIFIED | CLOSED`
- Priority: `LOW | MEDIUM | HIGH | CRITICAL`
- DedupeRelationKind: `EXACT_IDENTITY | POSSIBLE_DUPLICATE | RELATED`

## Stable Identity

```text
improvement_id = improvement:<skill_id>:<root_cause_key>
root_cause_key = lowercase kebab-case
```

Regeln:

1. Gleiche Root Cause im gleichen Skill-Scope → gleicher `improvement_id`.
2. Neue Formulierung allein erzeugt keine neue Identität.
3. Unklare Identität darf nicht erraten werden (fail closed upstream).
4. Semantische Ähnlichkeit ist Candidate Evidence (`POSSIBLE_DUPLICATE` / `RELATED`), niemals automatische Gleichheit.
5. Merge/Supersession behält Lineage (`ImprovementMergeLineage`, `aliases`, `superseded_by_improvement_id`).

Hilfen: `normalize_root_cause_key()`, `build_improvement_id()`.

## Recurrence

`recurrence` ist **abgeleitet** aus der Anzahl gültiger Observation Events:

```text
recurrence = derive_recurrence(count(valid observations))
```

Agents dürfen keinen unabhängigen `recurrence++`-Counter führen. Der im `Improvement`-Record gespeicherte Wert ist eine abgeleitete Projektion, die Stores nach Append neu berechnen.

## Observation Idempotenz

Jede Observation braucht einen nicht-leeren `idempotency_key` (bzw. stabilen Source Fingerprint). Retries mit demselben Key dürfen kein zweites Event erzeugen — die Write-Boundary (#47) erzwingt das; der Contract macht den Key Pflicht.

## Lifecycle-Übergänge

Strukturell erlaubt:

```text
NEW         -> RECURRING | CLOSED
RECURRING   -> VALIDATED | CLOSED
VALIDATED   -> PLANNED | CLOSED
PLANNED     -> IMPLEMENTED | CLOSED
IMPLEMENTED -> VERIFIED | CLOSED
VERIFIED    -> CLOSED
CLOSED      -> (terminal)
```

Hilfen: `is_lifecycle_transition_allowed()`, `require_lifecycle_transition()`.

Management-Authority, Evidence-Gates und HOLD-Fälle gehören zur Workforce Board-Manager-Governance / `ImprovementManagementPort` — nicht in diesen Datenvertrag.

## Wiederverwendung bestehender Semantik

- `#37` Temporal / Provenance / Supersession: optionale `TemporalEnvelope`, `Provenance`, `ResolutionMeta` an Improvement/Observation.
- `#15` Source-/Evidence-Grundtypen bleiben reference-only; Work-Refs verweisen auf GitHub-Live-Truth statt sie zu spiegeln.
- `#8` Trust-/Resolution-Logik wird später konsumiert, hier nicht dupliziert.

## Mapping zum Workforce Finding Contract

| Aspekt | Workforce Finding V1.1 | Improvement V1 |
|---|---|---|
| Identität | `health:<repo>:<root-cause-slug>` | `improvement:<skill>:<root_cause_key>` |
| Event vs Aggregat | Finding = Root Cause; Delta = Beobachtung | Improvement = Root Cause; Observation = Event |
| Lifecycle | `NEW/RECURRING/WORSENED/IMPROVED/RESOLVED/NO_MATERIAL_CHANGE` | `NEW/RECURRING/VALIDATED/PLANNED/IMPLEMENTED/VERIFIED/CLOSED` |
| Recurrence | steigt nur bei neuer bestätigender Evidence | abgeleitet aus Observation-Count |
| Mutation | Scouts advisory; keine auto Follow-up Issues | Observation Write ≠ Management Write ≠ GitHub Issue Create |
| Scope | Repo Health / Scout findings | Skill Learning / Improvement Blackboard |

Die Modelle sind **verwandt, aber nicht identisch**. Kein automatisches 1:1-Mapping der Lifecycle-Werte. Findings bleiben Health-Book-/Scout-Artefakte; Improvements sind die Skill-Learning-Domain in Agent Brain.

## Harte Grenze

Nicht Teil von #46:

- Storage Backend / Adapter
- `ImprovementObservationStore` Write-Port (#47)
- Dedupe-Runtime (#49)
- Management Port (#52)
- CLI/MCP Surface (#50)
- Markdown/Obsidian Projection (#51)
- Workforce Board-Manager-Authority oder GitHub Issue Create
- Änderungen an `KnowledgeStore` / `MemoryStore`
