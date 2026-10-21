# Slice 8 — Evidence, Decisions und Trust Design

**Issue:** #8 — Evidence, Decisions und Trust extrahieren  
**Status:** Design-Spec zur menschlichen Review — keine Implementierung  
**Vorgänger:** #7 / Slice 7 — Hybrid Retrieval / Knowledge Reasoning  
**Nachfolger:** #10 / Slice 9 — SurrealDB Read Runtime  
**Claire-Extraction-Baseline:** `Claire_de_Binare@84b5e05765fcde402a2565aa37fd42081ee95355`  
**Stand:** 2026-10-21

## Context

Slice #7 liefert den produktneutralen Retrieval-Layer. Slice #8 beantwortet die nächste Frage: **Wie belastbar sind gefundene Claims, Evidence und Entscheidungen?** Der Slice-0-Canon weist Evidence Resolution, Decision Replay, Contradiction/Stale/Scope Drift, Quality und Trust explizit #8 zu. `EvidenceRef` und `ClaimRef` sind bereits in #15 kanonisiert und bleiben reference-only.

Die Claire-Baseline enthält die fachliche Referenzlogik, aber vermischt portable Mechanik mit Produktvokabular, Operator-Policy, lokalen Pfaden, nicht injizierter Zeit und späteren DB-/Memory-/Protocol-Flächen. Slice #8 extrahiert nur den generischen, deterministischen Core.

```text
#15 Contracts → #7 Retrieval → #8 Evidence/Decisions/Trust → #10 DB-Read → #11 Memory
```

## Goal

Slice #8 liefert eine **produktneutrale, deterministische, side-effect-freie Signal-Pipeline**:

1. Claim↔Evidence Resolution auf `EvidenceRef`/`ClaimRef`.
2. Decision History + Decision Replay als Erklärung, nie Autorisierung.
3. Explizite Integrity-Findings für Contradiction, Freshness/Stale und Scope Drift.
4. Quality Assessment über sieben strukturierte Dimensionen.
5. Trust Summary mit `strong` / `partial` / `insufficient` und eigener Evidence-Sufficiency.

Alle Stufen laufen in-memory, ohne Netzwerk, DB oder versteckte Wall Clock.

## Non-Goals

Slice #8 enthält **nicht**:

- SurrealDB-Runtime, SurrealQL, DB-Client, DB-Auth oder produktive DB-Reads → #10.
- Jede Memory-Semantik einschließlich Read, Trust, TTL, Freshness und Writes → #11 bzw. späterer Write-Scope.
- MCP-/Protocol-Server oder CLI als Core-Abhängigkeit → #12.
- Claire-Imports, `CDB_*`-Pflichtnamen, Produkt-/Markt-/Freigabesemantik oder Operator-Level.
- GitHub-Live-/Ledger-vs-Live-Policy.
- eine zweite Definition oder v2-Erweiterung von `EvidenceRef` / `ClaimRef`.
- einen monolithischen `TrustEngine` oder Service-Container.

## Existing Foundations

| Foundation | Verwendung in #8 |
| --- | --- |
| `EvidenceRef`, `ClaimRef` | Identität und Referenzbeziehungen; keine Trust-/Resolver-Autorität |
| `ArtifactRef`, `RepositorySource`, `RepositoryProfile` | Scope-/Provenienzbezug |
| `IndexRecord`, `GraphEdge` | Coverage / Dependency Confidence |
| `canonical_json_dumps`, `canonical_hash`, `sha256_hex` | stabile IDs, Hashes, Fixture-Vergleiche |
| `require_compatible_version`, Contract Registry | Versionierung neuer #8-Verträge |
| Contract Serialization | kanonische Result-Ausgabe |
| Slice-7 Contract-/Policy-Stil | immutable Contracts + injizierbare Policy + kleine Public Surface |

**Grundregel:** #15 bleibt Identität + Referenzen. #8 ergänzt Lebenszykluszustand + Resolution über additive Overlay-Contracts.

Drei Invarianten tragen den Slice:

1. Status wird vom Producer deklariert, nicht heimlich aus anderen Daten abgeleitet.
2. Zeitabhängige Bewertung erfolgt nur an explizit zeitabhängigen Grenzen mit injiziertem `as_of`.
3. Quality und Trust aggregieren bereits berechnete Resultate; sie rufen keine vorgelagerte Fachlogik erneut auf.

## Claire Source Characterization

Charakterisiert gegen die gepinnte Baseline `84b5e05765fcde402a2565aa37fd42081ee95355`.

| Claire-Fläche | Entscheidung | Portables Verhalten / Grenze |
| --- | --- | --- |
| `claim_resolver.py` | MOVE | Claim-Auswahl, Status-Buckets, Missing/Unresolved Evidence; Autoritätstexte entfernen |
| `evidence_lookup.py` | MOVE | Evidence-Auswahl/Stärke; Wall Clock entfernen; Freshness aus Resolver herauslösen |
| `claim_evidence_at_rest.py` Struktur-/Metadata-Gate | MOVE | Caller-Metadaten ersetzen keine Evidence |
| `claim_evidence_at_rest.py` DB-Pfad | DEFER #10 | SurrealQL/Adapter/DB |
| `claim_evidence_proof_runtime.py` | DEFER #10/#12 | DB/tmp/Env/Runtime-Proof |
| `claim_evidence_proof_cli.py` | DEFER #12 | CLI |
| `decision_history_query.py` | MOVE | current/superseded/invalidated, Chain, Filter |
| `decision_replay_builder.py` | MOVE | Replay, Ref-Status, Chain-Hash; Clock entkoppeln |
| `contradiction_scan.py` Finding-Modell | MOVE | explizite Findings |
| `contradiction_scan.py` generische Regeln | MOVE | 3 generische Regeltypen über RuleSet |
| übrige Contradiction-Regeln | DEFER #12/#13 | benötigen spätere Shapes, Memory oder Live-Surface |
| `contradiction_cli.py` | DEFER #12 | CLI |
| `stale_knowledge_scan.py` | MOVE reduziert | 7 generische Stale-Typen; Memory-TTL nach #11 |
| `stale_refresh_plan.py` | MOVE reduziert | nur Empfehlungen; keine Workflow-/Write-Autorität |
| `stale_context_cli.py` | DEFER #12 | CLI |
| `scope_drift_firewall.py` Mechanik | MOVE | Scope-/Pfad-/Issue-/Surface-Vergleich |
| `scope_drift_firewall.py` Produktpolicy | ADAPTER | Pfade/geschützte Surfaces/Token beim Consumer |
| `scope_drift_blocking.py` | MOVE | generische Blocking-Ausgabe |
| `scope_drift_cli.py` | DEFER #12 | CLI |
| `quality_scoring.py` Mechanik | MOVE | 7 Dimensionen, Policy-isolierte Defaults |
| `quality_scoring.py` Memory-Dimension | DEFER #11 | vollständig aus #8 entfernen |
| `quality_scoring_cli.py` | DEFER #12 | CLI |
| `trust_summary.py` Mechanik | MOVE | Evidence/Claims/Decisions; keine Memory-Komponente |
| `trust_summary.py` Operator-/Live-Policy | DEFER #13 | Operator-Level, Repo-/Live-Heuristik |
| `negative_controls.py` | MOVE nur Invariante | keine Autorität/Secrets in Results; Write-Intent später |
| `negative_controls_matrix.py` | DEFER | Write-Scope |
| `architect_signals.py` | DEFER | Consumer/Readiness |
| `drift_report.py` | MOVE reduziert | Bericht über Findings |

### Erhaltenes Verhalten

- deterministische Claim↔Evidence-Verknüpfung;
- unresolved Evidence/Claim refs bleiben sichtbar;
- Claims ohne tragfähige Evidence werden nie als harte Wahrheit präsentiert;
- disputed / stale / invalidated / superseded bleiben explizit;
- Decision Replay erklärt und autorisiert nie;
- Contradiction, Stale und Scope Drift werden als Findings materialisiert, nicht still gefiltert;
- gleiche logische Inputs ergeben gleiche Ordnung, IDs und Hashes.

### Bewusste Abweichungen

- Scope-Matching exakt statt Claire-Substring-Verhalten.
- einheitliches Trimmen von Query-Selektoren.
- Wall Clock → explizites `as_of`.
- `by_freshness` aus Evidence Resolution entfernen; Freshness ausschließlich in `freshness.py`.
- produktbezogene Freigabefelder → opake `authorization_refs`.
- Produkt-/Operator-Level nicht übernehmen.
- Memory vollständig #11.
- Workflow-Overrides wie `false_positive` / `accepted_risk` nach #12.

## Architecture

### Fünf Stufen

```text
#15 EvidenceRef / ClaimRef + #8 Overlays
        ↓
1. Resolution
   resolve_evidence / resolve_claims
        ↓
2. Decisions
   query_decision_history / build_decision_replay
        ↓
3. Integrity
   detect_contradictions | evaluate_freshness | detect_scope_drift
        ↓
4. Quality
   score_quality
        ↓
5. Trust
   build_trust_summary
        ↓
structured explanation + limitations
```

Stufe 3 besteht aus drei parallelen, unabhängigen Komponenten. Keine Stufe ruft eine spätere auf. Quality und Trust importieren Result-Typen, nicht die Fachlogik der Nachbarstufen.

## Package / Module Boundaries

```text
src/agent_brain/evidence/
    __init__.py
    contract.py
    resolver.py
    decisions.py
    contradiction.py
    freshness.py
    scope_drift.py
    quality.py
    trust.py
```

- `agent_brain.contracts.evidence` = Referenzverträge (`EvidenceRef`, `ClaimRef`).
- `agent_brain.evidence` = Resolution und Assessment.
- kein `cli.py`, `mcp.py`, `health.py`, Service-Container oder State Holder.

## Contracts

### Typ A — Public Versioned Contracts

Serialisierbar und grenzüberschreitend: `schema_version`, `frozen=True`, `slots=True`, Validation, `to_dict`/`from_dict`, Compatibility Check.

**Overlays**

- `EvidenceState`: `evidence_id`, `strength`, `confidence`, `status`, `observed_at`, `expires_at`, `source_hashes`.
- `ClaimState`: `claim_id`, `status`, `scope`, `topics`, `updated_at`, `superseded_by`, `invalidated_by`, `confidence`, `uncertainty`.
- `DecisionRecord`: `decision_id`, title/question/answer/type/status/scope/topics, issue/evidence/claim/artifact refs, agent, `created_at`, supersession/invalidation, uncertainty, `authorization_refs`, `requires_evidence: bool = False`.

`requires_evidence` wird vom Producer deklariert. Der Core entscheidet nicht selbst, ob Evidence erforderlich ist.

**Queries / Requests**

- `EvidenceQuery`
- `ClaimQuery`
- `DecisionQuery`
- `DecisionReplayQuery`
- `TrustRequest`

**Results**

- `EvidenceResolution`
- `ClaimResolution`
- `DecisionHistoryResult`
- `DecisionReplay`
- `ContradictionFinding` / `ContradictionScanResult`
- `StaleFinding` / `FreshnessReport`
- `ScopeDriftFinding` / `ScopeDriftReport` / `ScopeDriftBlocking`
- `QualityDimensionScore` / `QualityAssessment`
- `TrustSummary`

**Policies**

- `QualityPolicy`
- `TrustPolicy`
- `FreshnessPolicy`
- `ScopeDriftPolicy`
- `EvidenceResolutionPolicy`
- `ClaimResolutionPolicy`

Policies sind immutable, deterministisch und frei von host-/repo-/produktspezifischen Defaults. Mapping-Felder werden readonly materialisiert.

### Typ B — Internal Immutable Input Types

Nicht als Prozess-/Dateivertrag serialisiert; immutable und validiert:

- `SourceState`
- `ArtifactState`
- `SurfaceState`
- `FreshnessBundle`
- `ContradictionBundle`
- `ScopeDriftBundle`
- `ContradictionRule`
- `ContradictionRuleSet`

Rule-/Bundle-Typen dürfen Funktionsreferenzen bzw. heterogene Domain-Records halten und sind deshalb bewusst keine Schema-Verträge.

### Generische Vokabulare

```text
EVIDENCE_STRENGTH_LEVELS = none, weak, moderate, strong, blocking_missing
EVIDENCE_STATUSES = active, revoked, unknown
CLAIM_STATUSES = unknown, proposed, supported, weakly_supported, disputed, superseded, stale, invalidated
DECISION_STATUSES = accepted, proposed, parked, superseded, invalidated, unknown
SEVERITY_LEVELS = info, warning, blocking
FINDING_STATUSES = open, resolved, refreshed, superseded
QUALITY_GRADES = blocking, watch, weak, good
TRUST_LEVELS = strong, partial, insufficient
EVIDENCE_SUFFICIENCY_LEVELS = sufficient, partial, insufficient
```

`unknown` ist neutral und nie positiv. Consumer-Workflow-Zustände wie `false_positive`, `accepted_risk` oder `accepted_stale` sind nicht Teil der #8-Core-Semantik.

## Data Flow

| Stufe | Eingang | Ausgang | `as_of` |
| --- | --- | --- | --- |
| Resolution | #15 Refs + #8 State + Query/Policy | `EvidenceResolution`, `ClaimResolution` | nein |
| Decisions | `DecisionRecord[]` + Query | `DecisionHistoryResult`, `DecisionReplay` | History nein, Replay ja |
| Integrity | Bundles + Policies | Contradiction/Freshness/Scope Results | ja |
| Quality | Resultate 1–3 + `SurfaceState[]` + Policy | `QualityAssessment` | ja |
| Trust | TrustRequest + Resultate 1/2/4 + Policy | `TrustSummary` | übernimmt Assessment-Zeit |

Datenqualitätsprobleme werden als Warnungen/Limitations/Findings sichtbar. Strukturell ungültige Requests oder Contracts schlagen fail-closed fehl.

## Evidence / Claim Resolution

Resolution löst **Identität, Beziehungen und deklarierten Zustand**, aber keine Zeit.

### `resolve_evidence`

```python
def resolve_evidence(*, evidence, states=(), query=None, policy=None) -> EvidenceResolution
```

- Overlay per `evidence_id`; orphan States erzeugen Warnung.
- Stärke aus `EvidenceState`; fehlt State, konservative Policy-Ableitung; nie `strong` ohne tragfähige Provenienz.
- Producer-Status wird nur durchgereicht und gezählt.
- Query-Modi: Artifact, Claim, Decision, Source, Evidence Type, Strength, Status.
- **kein** `by_freshness`, **kein** `as_of`, **keine** Expiry-/Age-Auswertung.

### `resolve_claims`

```python
def resolve_claims(*, claims, states=(), evidence=(), query=None, policy=None) -> ClaimResolution
```

- fehlt `ClaimState`, Status `unknown` + sichtbare Warnung;
- `ClaimRef.evidence_refs` wird gegen bekannte `EvidenceRef.evidence_id` aufgelöst;
- unresolved refs und missing-evidence Claims bleiben explizit;
- Buckets: disputed / stale / invalidated / superseded / missing-evidence;
- keine Resolution erzeugt Autorität.

Sortierung erfolgt stabil über gespeicherte Zeitstempel + ID; undatierte Records stehen hinten. Input-Reihenfolge ändert das Ergebnis nicht.

## Decision History / Replay

### `query_decision_history`

- Bucketing: invalidated vor superseded vor current.
- Supersession Chains zyklussicher über `visited`.
- dangling links bleiben sichtbar (`broken_supersession_chain`).
- fehlen bekannte Evidence-/Claim-ID-Mengen, gilt Resolution als **nicht durchgeführt**, nicht als erfolgreich.

### `build_decision_replay`

```python
def build_decision_replay(*, decisions, query, as_of, known_evidence_ids=None,
                          known_claim_ids=None, evidence_summaries=None,
                          claim_summaries=None) -> DecisionReplay
```

- Replay erklärt nur.
- historische Buckets bleiben vom Sichtbarkeitsfilter getrennt.
- `decision_chain_hash` schließt `as_of` aus.
- unresolved refs bleiben sichtbar.
- `authorization_refs` werden durchgereicht, nie ausgewertet.
- `authorization_implied` ist immer `False`.

## Contradiction

Contradiction trennt portable Findings von einer injizierbaren RuleSet-Policy.

`ContradictionRule` trägt `rule_id`, `rule_type`, `severity`, `confidence`, Beschreibung, Empfehlung und pure Detector-Referenz. Severity/Confidence sind **Daten der Regel**, keine im Algorithmus verteilten Literale.

Default-Scope: drei generische Claire-basierte Regeltypen:

- `claim_vs_evidence`
- `decision_vs_evidence`
- `stale_decision_vs_new_evidence`

Weitere Claire-Regeln, die spätere Shapes, Memory oder Live-Surface brauchen, bleiben deferred. Findings sind deterministisch sortiert und erhalten stabile IDs aus canonical hash. Workflow-Overrides sind nicht Teil des Core.

## Freshness / Stale

Freshness ist die **einzige** #8-Komponente, die Zeitstempel gegen einen Referenzzeitpunkt auswertet.

```python
def evaluate_freshness(*, bundle: FreshnessBundle, policy=None, as_of) -> FreshnessReport
```

Generische Stale-Typen:

- `source_hash_changed`
- `source_deleted`
- `decision_superseded`
- `evidence_expired`
- `dependency_edge_no_longer_observed`
- `stale_context_package`
- `stale_briefing`

`memory_ttl_expired` gehört #11.

Mechanismen: Expiry vs. `as_of`, Freshness Window, Snapshot Identity. Fehlende/unparsbare Zeitinformation erzeugt keine künstliche Freshness und keine unbelegte Stale-Behauptung; sie erzeugt Warnung/Limitation.

Refresh-Ausgabe bleibt Empfehlung (`reverify_source`, `refresh_evidence`, `recheck_decision`, `rebuild_context_package`, `regenerate_briefing`, `reobserve_dependency_edge`, `manual_review`) und trägt keine Write-Autorität.

## Scope Drift

Scope Drift trennt Mechanik von Consumer-Policy.

```python
def detect_scope_drift(*, bundle: ScopeDriftBundle,
                       policy: ScopeDriftPolicy,
                       as_of) -> ScopeDriftReport
```

`ScopeDriftPolicy` ist Pflichtparameter. Der Core kennt keine produktspezifischen Pfade oder Surface-Kataloge.

Generische Drift-Typen:

- `path_out_of_scope`
- `forbidden_surface_touched`
- `runtime_surface_touched`
- `unauthorized_write_intent`
- `missing_authorization_for_write_mode`
- `domain_out_of_scope`
- `issue_out_of_scope`
- `unexpected_dependency_expansion`

Pfadvergleich respektiert Verzeichnisgrenzen; Globs sind explizit. Leere `target_paths` deaktivieren nur die Pfadregel.

### Authorization references

`authorization_refs` sind opake Referenzen. Der Core darf Presence prüfen, wenn eine generische Policy das verlangt. Er darf **nicht** Gültigkeit prüfen, eine Freigabe ableiten oder Referenzinhalte interpretieren.

**Presence ≠ Authorization.**

## Quality Scoring

Slice #8 bewertet **genau sieben** Dimensionen:

1. coverage
2. freshness
3. evidence
4. contradiction
5. dependency_confidence
6. decision_validity
7. scope_risk

Memory existiert weder als aktive noch als optionale Dimension.

```python
def score_quality(*, scope_id, as_of, level="system", surfaces=(),
                  evidence_resolution=None, claim_resolution=None,
                  decision_history=None, contradictions=None,
                  freshness=None, scope_drift=None,
                  policy=None) -> QualityAssessment
```

Mechanik:

- Zähldimensionen: erfüllte Kriterien / verfügbare Kriterien.
- invers penalisierende Dimensionen: `max(0, 1 - Σ penalty)`.
- Freshness wird aus `FreshnessReport` abgeleitet, nicht neu berechnet.
- fehlende Dimensionen werden nicht mit neutralem `0.5` erfunden; sie werden ausgelassen und als Limitation sichtbar.
- alle Gewichte, Grade-Bänder, Penalties und Thresholds liegen in `QualityPolicy`, nicht versteckt im Algorithmus.

## Trust Summary

`TrustSummary` ist Assessment, nicht Autorität.

```text
TRUST_LEVELS = strong, partial, insufficient
EVIDENCE_SUFFICIENCY_LEVELS = sufficient, partial, insufficient
```

Genau drei Trust-Komponenten:

- evidence → `EvidenceResolution`
- claims → `ClaimResolution`
- decisions → `DecisionHistoryResult`

Keine Memory-Komponente.

`TrustPolicy.required_components` ist standardmäßig Evidence + Claims + Decisions. Fehlt eine Pflichtkomponente, darf das Ergebnis nie `strong` werden; fehlen alle Komponenten, ist es `insufficient`. Blocking Findings erzwingen `insufficient` und bleiben sichtbar.

`evidence_sufficiency` trägt AC5 unabhängig vom Gesamtscore direkt maschinenlesbar.

## Policy Boundaries

> Der Core enthält keine **produktspezifischen** Zahlen. Alle Score-, Threshold-, Penalty- und Gewichtungswerte liegen in expliziten Policy- oder RuleSet-Objekten.

Neutrale Defaults sind erlaubt, aber nicht als verstreute Magic Numbers.

- Quality: verfügbare Dimensionen standardmäßig gleich gewichtet.
- Trust: Evidence/Claims/Decisions standardmäßig gleich gewichtet.
- Grade-/Trust-Bänder ausschließlich in `QualityPolicy.default()` / `TrustPolicy.default()`.
- Severity-Penalties ausschließlich in Policy.
- Contradiction Severity/Confidence ausschließlich im RuleSet.
- Freshness Window ausschließlich in `FreshnessPolicy`.
- Scope-Pfade/Surfaces ausschließlich in Consumer-Policy.

Claire-spezifische Zahlen werden nur in einer Test-Fixture-Policy materialisiert, um numerische Parity zu beweisen, nicht als Runtime-Default.

## Determinism

- stabile Sortierung über IDs und gespeicherte Zeitstempel;
- keine Set-/Dict-Iterationsreihenfolge in Outputs;
- keine Randomness;
- keine implizite Wall Clock;
- kein Slice-8-Modul ruft `utcnow()`, `SystemClock()`, `datetime.now()` oder `datetime.utcnow()` auf;
- Consumer erzeugt explizites `as_of`;
- canonical serialization/hash über bestehende Foundation;
- gleiche logische Inputs → identische IDs, Reihenfolge und Hashes.

`decision_chain_hash` schließt `as_of` bewusst aus.

## Conservative Defaults

| Situation | Verhalten |
| --- | --- |
| Evidence fehlt | keine starke Trust-Aussage |
| Evidence-Ref unbekannt | unresolved + sichtbar |
| `EvidenceState` fehlt | konservative Stärke; nie künstlich strong |
| `ClaimState` fehlt | `unknown` + Warnung |
| malformed / NaN / Inf Score | kein positiver Beitrag + Warnung |
| Zeitstempel fehlt | weder Freshness noch Stale behaupten + Warnung |
| Contradiction / Stale / Scope Drift | sichtbares Finding |
| bekannte ID-Mengen fehlen | Resolution nicht durchgeführt + Warnung |
| unbekannter Finding-Status | konservativ aktiv + Warnung |
| Trust-Pflichtkomponente fehlt | höchstens partial |
| keine Trust-Komponente | insufficient |
| Quality-Dimension fehlt | nicht aggregieren, Limitation sichtbar |

Fehlende Information erzeugt nie künstliche Sicherheit.

## Error Handling

Fehlerfamilie:

```text
ValueError
└── EvidenceError
    ├── ResolutionError
    ├── DecisionError
    ├── ContradictionError
    ├── FreshnessError
    ├── ScopeDriftError
    ├── QualityError
    └── TrustError
```

Strukturell ungültige Inputs, Query-Modi, Limits, IDs, Schema-Versionen und Policies schlagen fail-closed fehl. Datenqualitätsprobleme wie unresolved refs, fehlende Overlays oder unparsbare Zeitstempel werden sichtbar materialisiert statt still geschluckt.

## Security / Authority Boundaries

Generische Guardrails:

```text
Assessment only; does not grant authorization.
No automatic mutation or write.
Resolution and scoring are informational outputs.
Authorization is a consumer responsibility.
```

Kein Result darf Felder besitzen, die eine Freigabe behaupten, z. B. `approved`, `go`, `live_go`, `human_go`, `authorization_granted`, `permission_granted`, `execution_allowed`.

Zulässig sind nur beschreibende Felder wie:

- `authorization_refs` — opake Referenzen;
- `authorization_required` — Policy verlangt Referenz;
- `authorization_implied` — immer `False`.

Der Core liest keine externen Live-Systeme und mutiert nichts.

## Source → Target Mapping

| Quelle | Ziel |
| --- | --- |
| Claim/Evidence Resolver + Evidence Lookup | `evidence/resolver.py` |
| Decision History + Replay | `evidence/decisions.py` |
| Contradiction Finding + 3 Default-Regeltypen | `evidence/contradiction.py` |
| 7 generische Stale-Typen | `evidence/freshness.py` |
| Scope-Drift-Mechanik + Blocking-Ausgabe | `evidence/scope_drift.py` |
| 7 Quality-Dimensionen | `evidence/quality.py` |
| 3 Trust-Komponenten | `evidence/trust.py` |
| DB-Pfade / Proof Runtime | #10 / #12 |
| Memory-Semantik | #11 |
| CLI/MCP Surfaces | #12 |
| Operator-/Live-/Repo-Policy | #13 |
| produktive Write-/Audit-Semantik | späterer Write-Scope |

## Parity / Test Strategy

Parity bedeutet Contract-Parity, nicht Dateikopie.

### PORT

- Evidence-/Claim Resolver-Modi und Determinismus.
- Claim/Evidence-Struktur- und Metadata-Gates ohne DB.
- Decision History / Replay / Chain / Hash.
- 3 generische Contradiction-Regeltypen.
- 7 Freshness-Regeln ohne Memory.
- 8 generische Scope-Drift-Regeln ohne Produktpolicy.
- 7 Quality-Dimensionen.
- generische Trust-Summary-Mechanik.
- Cross-Cutting Visibility und Conservative Defaults.

### PARITY ONLY

- Claire-spezifische Zahlen über `tests/fixtures/evidence/claire_parity_policy.v1.json`.
- Claire-Fixtures bleiben Referenzmaterial; sie werden nicht blind kopiert.

### DEFER

- DB/local proof → #10.
- Memory → #11.
- CLI/MCP → #12.
- Operator-/Live-/Repo-Policy und Produktadapter → #13.
- Write-Intent-/Audit-Write → separater Write-Scope.

### Neue Agent-Brain-Testgruppen

- `test_product_neutrality.py`
- `test_determinism.py`
- `test_conservative_defaults.py`
- `test_policy_isolation.py`
- `test_claire_parity_policy.py`
- `test_no_authority_signals.py`
- `test_public_surface.py`
- `test_fixtures.py`
- `test_freshness_separation.py`
- `test_contract_inventory.py`
- Resolver-, Decision-, Contradiction-, Freshness-, Scope-, Quality- und Trust-spezifische Tests.

Neutrale Fixtures liegen später unter `tests/fixtures/evidence/`; Claire-Zahlen dürfen ausschließlich in der Parity-Policy-Fixture vorkommen.

## Acceptance Criteria Mapping

| AC | Design / Evidence |
| --- | --- |
| AC1 deterministische Claim↔Evidence-Zuordnung | `resolve_evidence` / `resolve_claims`, stabile Ordnung, unresolved refs sichtbar |
| AC2 #15 Contracts konsumieren | unveränderte `EvidenceRef` / `ClaimRef`, additive #8-Overlays |
| AC3 Replay erklärt, autorisiert nicht | opake refs, `authorization_implied=False`, limitations |
| AC4 Contradiction/Stale/Scope Drift sichtbar | versionierte Finding-/Report-Contracts |
| AC5 strong/partial/insufficient | Trust Levels + `evidence_sufficiency` |
| AC6 Claire-Contracts abgedeckt | PORT/PARITY/DEFER-Matrix + injizierte Parity Policy |
| AC7 keine Claire-spezifische Produktsemantik | Neutrality-/Policy-Isolation-Tests und generische Core Surface |

## Deferred Work

- #10: SurrealDB Read Runtime, DB Adapter, SurrealQL, DB Proof.
- #11: gesamte Memory-Semantik, inklusive Memory Trust/TTL/Rules.
- #12: CLI, MCP/Protocol, Workflow Overrides, P0–P3 Refresh Workflow.
- #13: Claire-/Repo-/Live-/Operator-Policy und produktiver Adapter.
- separater Write-Scope: produktive Memory-/Audit-Writes und Write-Intent Governance.

## Proposed Implementation Slices

Noch **kein** Implementation Plan; nur Architektur-Reihenfolge:

1. Result-, Policy-, Overlay- und Query-Contracts.
2. Evidence-/Claim-Resolution ohne Zeitauswertung.
3. Decision History + Replay.
4. Contradiction Detection + Default RuleSet.
5. Freshness + Scope Drift.
6. Quality Scoring (7 Dimensionen).
7. Trust Summary (3 Komponenten).
8. Neutrales E2E + Claire Parity + Public Surface + Doku.

Spätere Umsetzung ist test-first. Slice 8 aktualisiert erst bei tatsächlicher Implementierung `docs/START_HIER.md`, `docs/DATENFLUESSE.md` und `docs/contracts/README.md`.

## Open Questions

1. **Quality-Gewichte:** neutral gleich gewichtet vs. Claire-Gewichte? Empfehlung: gleich gewichtet + Parity-Fixture.
2. **Grade-Bänder:** generischer Default oder gar kein Default? Empfehlung: Default nur in `QualityPolicy.default()`.
3. **Zeit-API:** explizites `as_of` vs. Clock-Parameter? Empfehlung: explizites `as_of`.
4. **Severity-Penalties:** konservativer Core-Default vs. weichere Claire-Werte? Empfehlung: konservativer, injizierbarer Default.
5. **`ScopeDriftPolicy` Pflichtparameter?** Empfehlung: ja; ohne Policy wäre der Aufruf Scheinsicherheit.
6. **`TrustPolicy.required_components`:** Core-Default alle drei oder Consumer? Empfehlung: alle drei als konservativer Default.
7. **Finding Exemptions:** Vocabulary im Core, Auswahl in Policy? Empfehlung: ja.

Bereits entschieden: Paketname `agent_brain.evidence`; Overlay-Design statt #15-v2; Trust-Level `strong/partial/insufficient`; `evidence_sufficiency`; Contradiction Default-Scope = 3 Regeltypen; Memory vollständig #11; fünf Pipeline-Stufen; `authorization_refs` opak.

## Review Focus

1. Overlay-Design: #15 Identität/Referenzen vs. #8 Lebenszyklus/Auflösung.
2. Contract-Inventar und Typ-A/Typ-B-Grenze.
3. Policy-/RuleSet-Isolation und Claire-Parity.
4. Resolver/Freshness-Trennung.
5. Explizite `as_of`-Semantik.
6. Trust- und Evidence-Sufficiency-Vokabular.
7. `Presence ≠ Authorization` in Scope Drift und Replay.
8. Contract-Parity plus injizierte numerische Parity.
9. sauberer Deferred-Rand für DB, Memory, Protocol, Live-Policy und Writes.
10. Produktneutralität aller Core-APIs, Defaults und Guardrails.

## Review Decision Gate

Diese Datei ist eine **Design-Spec zur menschlichen Review**, keine Implementierungsfreigabe.

Bis zum Design-Review:

- Issue #8 bleibt `PLANNED`.
- keine AC wird abgehakt.
- keine Produktionsmodule unter `src/agent_brain/evidence/` werden angelegt.
- kein detaillierter Implementation Plan wird ausgeführt.
- der Review-PR wird nicht ohne expliziten Design-Review gemergt.

**Zielzustand:** `SPEC_REVIEW_READY`.
