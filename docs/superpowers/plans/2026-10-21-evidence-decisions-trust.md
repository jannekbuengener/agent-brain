# Slice 8 — Evidence, Decisions und Trust Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Issue #8 [SLICE 8] — produktneutrale Evidence-/Decision-/Trust-Komponente auf Basis der kanonischen #15-Referenzverträge (`EvidenceRef`, `ClaimRef`) und der gemergten #37-Contracts (`TemporalEnvelope`, `Provenance`, `SourceSpan`, `ResolutionMeta`, `ResolutionState`). Liefert deterministische Claim↔Evidence-Auflösung, Decision History/Replay, explizite Integrity-Findings (Contradiction, Freshness/Stale, Scope Drift), Quality Assessment und Trust Summary — ohne Produktlogik, ohne DB, ohne Memory, ohne Autorität.

**Architecture:** Neuer Layer `src/agent_brain/evidence/` mit neun Modulen. Fünfstufige, gerichtete Signal-Pipeline: Resolution → Decisions → Integrity → Quality → Trust. Stufe 1 löst Identität, Beziehungen, deklarierten Zustand und Provenance-Konflikte auf (ohne `as_of`). Stufe 3 ist die einzige zeitbewusste Stufe und leitet dort die `ResolutionState` aus den #37-Inputs ab. Stufe 4 aggregiert bereits berechnete Resultobjekte, Stufe 5 bewertet sie. Alle Stufen side-effect-free, in-memory, deterministisch, ohne versteckte Wall Clock.

**Tech Stack:** Python >= 3.12, Standardbibliothek, pytest, Ruff. Keine neuen Runtime-Dependencies, keine zusätzlichen Package-Dependencies.

**Spec:** `docs/superpowers/specs/2026-10-21-evidence-decisions-trust-design.md` (gemergt in `main` als `783504c`) — Issue #8 (OPEN, 10 ACs) — `docs/superpowers/specs/2026-10-21-temporal-provenance-contract-design.md` (#37-Contract-Semantik) — `docs/contracts/README.md` — `docs/extraction/COMPONENT_OWNERSHIP.md` (§ 2.7 Slice-8-MOVE-Flächen) — `docs/extraction/PARITY_GATES.md` (Slice-8-Parity-Gate-Tests) — `docs/START_HIER.md` — `docs/DATENFLUESSE.md`.

## Global Constraints

1. **#15 bleibt reference-only.** `EvidenceRef`/`ClaimRef` werden unverändert konsumiert. Keine Zweitdefinition, kein v2-Bump, keine Feld-Erweiterung in `agent_brain/contracts/evidence.py`.
2. **#37 bleibt Contract-Owner.** `known_at`, `valid_from`, `valid_until`, `system_as_of`, `source_kind`, `source_ref`, `source_hash`, `source_span`, `source_session_id`, `source_turn_at`, `derived_from`, `supersedes_ref`, `superseded_by_ref`, `supersession_reason`, `source_trust`, `confidence` und die `SourceSpan`-Offset-Semantik werden **konsumiert, nie nachgebaut**. Keine #8-Overlays mit eigenem Zeit-, Provenienz- oder Supersession-Feld.
3. **`ResolutionState` wird abgeleitet, nie gespeichert.** Die Enum kommt aus `agent_brain.contracts.resolution`. Kein #8-Contract führt ein persistiertes `resolution_state`-Feld.
4. **Ableitungsort ist kanonisch Stufe 3.** Die `ResolutionState`-Ableitung liegt in `freshness.py` und wird über `FreshnessReport.resolution_states` ausgeliefert. `resolver.py` bewertet **keine** Zeit.
5. **`source_trust` ≠ `confidence`.** Beide werden getrennt konsumiert, getrennt ausgewertet (`source_trust_assessment`, `confidence_assessment`) und **nie** voneinander abgeleitet, nie gegenseitig überschrieben, nie kollabiert. Kein Beitrag zum `composite_score`.
6. **Kein stilles Last-Write-Wins.** Kandidaten derselben logischen ID aus verschiedenen Provenance-Streams ohne Supersession bleiben alle sichtbar; es wird kein Gewinner gewählt; der Zustand wird konservativ `UNKNOWN`.
7. **Keine Score-Zahl im Algorithmus.** Alle Gewichte, Grade-Bänder, Severity-Penalties, Schwellen und Confidences liegen in `QualityPolicy`, `TrustPolicy`, `FreshnessPolicy`, `ScopeDriftPolicy`, `EvidenceResolutionPolicy`, `ClaimResolutionPolicy` oder im injizierten `ContradictionRuleSet`.
8. **Kein versteckter Clock.** Kein Modul importiert `agent_brain.core.time` und ruft `utcnow()`, `SystemClock()`, `datetime.now()` oder `datetime.utcnow()` auf. `as_of` wird ausschließlich als Pflichtparameter an den in der Spec festgelegten Stellen übergeben.
9. **`system_as_of` ist nie Fact-Zeit.** Es ist Read-/Snapshot-Metadatum und wird nie gegen Fakt-Zeiten verglichen.
10. **Resolver ≠ Freshness.** Kein `by_freshness`, keine Expiry-/Age-Auswertung, kein `stale_evidence_ids` im Resolver.
11. **Fünf Stufen, eine Richtung.** Keine Stufe ruft eine spätere auf; Quality und Trust importieren Typen, nicht Fachlogik der Nachbarstufen.
12. **Memory bleibt vollständig #11.** Keine Memory-Komponente, keine Memory-Dimension, kein `memory_trust_score`, kein `memory_component_enabled`, kein `MemoryStore`/`MemoryScope`.
13. **#10-Grenze.** Kein SurrealDB-Client, kein SurrealQL, keine Connection/Namespace/Auth, kein DB-Adapter.
14. **#12-Grenze.** Kein CLI, kein MCP-/Protocol-Surface, kein `argparse`-Shell.
15. **#13-Grenze.** Keine Claire-Policy, kein Operator-Level, kein Live-/Repo-Policy, keine produktiven Pfade im Core.
16. **Produktneutralität im Core.** Keine Produkt-, Markt-, Freigabe- oder Umgebungsbegriffe, keine Env-Präfixe, keine Host-Pfade, keine Anbieter-/Produktnamen in Core-Quelltext, Defaults, Policies oder Resultfeldern.
17. **Autorität:** Kein Result-Feld trägt einen autoritätsbehauptenden Namen. `authorization_refs` sind opak, `authorization_required` beschreibt eine Anforderung, `authorization_implied` ist immer `False`. **Presence ≠ Authorization.**
18. **Konservative Defaults.** Fehlende Information erzeugt nie künstliche Sicherheit: keine erfundenen neutralen `0.5`-Dimensionen, keine erfundenen `current`-Zustände, keine automatisch aufgelösten Evidence-Refs.
19. **Determinismus.** Stabile Sortierung über kanonische Schlüssel (`temporal.known_at` + ID), nie über dict-/set-/Input-Reihenfolge. Gleiche logische Inputs ⇒ identisches Ergebnis inklusive IDs und Hashes.
20. **Test-first RED→GREEN**, Ruff clean, statische Fixtures unter `tests/fixtures/evidence/`.

## Review Focus

Die fünf maßgeblichen Failure Classes — jede ist einem konkreten Task-Test zugeordnet:

1. **Cross-Provenance-Konflikt ohne Last-Write-Wins** → Task 4, `tests/evidence/test_cross_provenance_conflict.py`: zwei Kandidaten derselben `evidence_id` mit unterschiedlicher `provenance.source_ref` bleiben beide in der Resolution sichtbar, es existiert kein Gewinner-Feld, der Zustand ist `UNKNOWN`, und ein expliziter Supersession-Link verhindert den Falschkonflikt.
2. **`system_as_of` versehentlich als Fact-Zeit** → Task 5, `tests/evidence/test_temporal_semantics.py`: ein `system_as_of` vor `known_at` darf `STALE`/`UNKNOWN` nicht auslösen; `FreshnessReport` führt `system_as_of` ausschließlich als Snapshot-Metadatum.
3. **`source_trust`/`confidence` versehentlich gekoppelt** → Task 7, `tests/evidence/test_source_trust_confidence_separation.py`: Änderung von `source_trust` ändert `confidence_assessment` und `composite_score` nicht (und umgekehrt).
4. **Dangling/cyclic Supersession** → Task 3, `tests/evidence/test_supersession_semantics.py`: hängendes `superseded_by_ref` ⇒ `UNKNOWN` + Warnung `broken_supersession_chain`, keine stille Rückstufung auf `current`; Supersession-Zyklus terminiert und erzeugt keine Endlosschleife.
5. **Fehlende Signale erzeugen künstlich positive Quality/Trust** → Task 6/7, `tests/evidence/test_conservative_defaults.py`: fehlende Dimensionen werden ausgelassen (nicht `0.5`), fehlende Trust-Komponente deckelt auf `partial`, fehlende Evidence erzeugt nie `strong`/`sufficient`.

Weitere Review-Punkte: die `ResolutionState`-Präzedenz muss in Task 5 exakt `UNKNOWN > SUPERSEDED > STALE > CURRENT` sein; der Resolver darf unter keinen Umständen Zeit auswerten; alle Default-Zahlen müssen in Policies oder RuleSets auffindbar und nirgends im Algorithmus verteilt sein.

## Exact File Map

### Create

| Datei | Zweck |
|---|---|
| `src/agent_brain/evidence/__init__.py` | Öffentliche Surface (`__all__`) — Verhalten lives in den Modulen |
| `src/agent_brain/evidence/contract.py` | Alle #8-Typ-A-Contracts (Overlays, Queries, Results, Policies), Fehlerfamilie, lokale Validatoren, Vokabulare |
| `src/agent_brain/evidence/resolver.py` | `resolve_evidence`, `resolve_claims`, Cross-Provenance-Konflikterkennung |
| `src/agent_brain/evidence/decisions.py` | `query_decision_history`, `build_decision_replay` |
| `src/agent_brain/evidence/contradiction.py` | `ContradictionRule`, `ContradictionRuleSet`, `detect_contradictions` |
| `src/agent_brain/evidence/freshness.py` | `evaluate_freshness`, `ResolutionState`-Ableitung, `build_scope_drift_blocking`-freier Teil |
| `src/agent_brain/evidence/scope_drift.py` | `detect_scope_drift`, `build_scope_drift_blocking` |
| `src/agent_brain/evidence/quality.py` | `score_quality` |
| `src/agent_brain/evidence/trust.py` | `build_trust_summary` |
| `tests/fixtures/evidence/evidence_claims.neutral.v1.json` | Neutrale EvidenceRef/ClaimRef/EvidenceState/ClaimState-Menge |
| `tests/fixtures/evidence/decisions.neutral.v1.json` | Neutrale DecisionRecord-Menge inkl. Supersession-Kette |
| `tests/fixtures/evidence/cross_provenance_conflict.neutral.v1.json` | Konfliktfall zweier Provenance-Streams |
| `tests/fixtures/evidence/temporal_cases.neutral.v1.json` | known_at/valid_from/valid_until-Fälle |
| `tests/fixtures/evidence/scope_drift.neutral.v1.json` | Scope-Drift-Bundle |
| `tests/fixtures/evidence/quality_signals.neutral.v1.json` | Resultobjekte der Stufen 1–3 als Quality-/Trust-Input |
| `tests/fixtures/evidence/claire_parity_policy.v1.json` | **Einzige** Fundstelle Claire-spezifischer Zahlen |

### Modify

| Datei | Änderung |
|---|---|
| `docs/START_HIER.md` | Slice-8-Abschnitt ergänzen (erst in Task 8, bei realer Implementierung) |
| `docs/DATENFLUESSE.md` | Slice-8-Datenfluss-Mermaid ergänzen (Task 8) |
| `docs/contracts/README.md` | Producer-/Consumer-Richtung um Slice 8 ergänzen (Task 8) |

**Ausdrücklich nicht geändert:** `src/agent_brain/contracts/` (kein v2-Bump, keine Registry-Erweiterung — Slice-7-Präzedenz: slice-lokale Contract-Familien gehören nicht automatisch in `CONTRACT_SCHEMAS`), `pyproject.toml` (keine neue Dependency), `src/agent_brain/contracts/registry.py`.

### Tests (Fokus-Suite)

`tests/evidence/` — 21 Dateien, je Datei eine fachliche Verantwortung:

| Datei | Verantwortung |
|---|---|
| `test_evidence_contracts.py` | Typ-A-Contracts: Schema-Validierung, Versionierung, `to_dict`/`from_dict`, fail-closed, keine #37-Duplikation, kein persistiertes `resolution_state` |
| `test_resolution.py` | `resolve_evidence` / `resolve_claims`: Zuordnung, unresolved refs, orphan overlays, konservatives Missing-Evidence, kein Freshness-Scoring, stabile Sortierung |
| `test_cross_provenance_conflict.py` | Konfliktgruppen, kein Gewinner, kein Last-Write-Wins |
| `test_decision_history.py` | Buckets, Ketten, Cycle, dangling refs, bekannte ID-Mengen |
| `test_decision_replay.py` | Replay deterministisch, Chain-Hash, erklärend, `authorization_refs` opak |
| `test_contradiction.py` | RuleSet, 3 Claire-Regeltypen + `cross_provenance_conflict`, deterministische Finding-IDs |
| `test_resolution_state_derivation.py` | Vollständige Ableitungstabelle + Präzedenz (Task 5) |
| `test_temporal_semantics.py` | #37-Temporal-Konsum, `system_as_of` nie als Fact-Zeit |
| `test_supersession_semantics.py` | Supersession nur aus `ResolutionMeta`, dangling, Cycle |
| `test_freshness.py` | Stale-Typen, `validity_window_closed`, Dependency-Edge-Differenz |
| `test_scope_drift.py` | Pfad/Glob/Verzeichnisgrenze, Policy-Pflicht, Presence ≠ Authorization |
| `test_quality.py` | 7 Dimensionen, Grade-Bänder, Penalties, missing dimension, NaN/Inf |
| `test_trust.py` | 3 Komponenten, Level, `evidence_sufficiency`, `required_components`, blocking findings |
| `test_source_trust_confidence_separation.py` | Unabhängigkeit beider Werte, kein Beitrag zum Composite |
| `test_conservative_defaults.py` | Negativkontrollen-Katalog (siehe unten) |
| `test_determinism.py` | Reorder-Identität über alle Stufen, wiederholte Runs identisch |
| `test_product_neutrality.py` | Wortliste, keine Claire-/CDB-/Trading-Begriffe, keine Host-Pfade, kein DB/Netzwerk, keine Memory-Importe, kein Clock-Import |
| `test_no_authority_signals.py` | Verbotene Resultfelder, `authorization_implied` immer `False`, `limitations` nie leer |
| `test_public_surface.py` | `__all__` exakt wie spezifiziert |
| `test_claire_parity_policy.py` | Injizierte Parity-Policy reproduziert die veröffentlichten Claire-Zahlen |
| `test_e2e.py` | Volle Fünf-Stufen-Pipeline gegen neutrale Fixtures |

## Contract-Referenz (#37-Konsum, verbindlich)

Der Plan konsumiert exakt diese gemergten Typen. Es gibt keine #8-Gegenstücke.

```python
from agent_brain.contracts import (
    ClaimRef, EvidenceRef, Provenance, ResolutionMeta, ResolutionState,
    SourceSpan, TemporalEnvelope,
)
```

| Typ | Schema | Verwendungszweck in #8 |
|---|---|---|
| `TemporalEnvelope` | `temporal-envelope/v1` | Zeitliche Hülle aller Overlays; `known_at` (Pflicht) trägt Sortierung, `valid_from`/`valid_until` die Gültigkeitsprüfung, `system_as_of` nur Snapshot-Metadatum |
| `Provenance` | `provenance/v1` | Herkunft; `source_ref`/`source_hash` bilden die Provenance-Identität der Konflikterkennung |
| `SourceSpan` | (Value Type) | nur durchgereicht; #8 validiert keine Span-Semantik |
| `ResolutionMeta` | `resolution-meta/v1` | `supersedes_ref`, `superseded_by_ref`, `supersession_reason`, `source_trust`, `confidence` |
| `ResolutionState` | (StrEnum) | `CURRENT`, `STALE`, `SUPERSEDED`, `UNKNOWN` — Zielwert der #8-Ableitung |

Konstruktor-Signaturen (aus `main`, unverändert zu übernehmen):

```python
TemporalEnvelope(schema_version, known_at, valid_from=None, valid_until=None, system_as_of=None)
Provenance(schema_version, source_kind, source_ref, source_hash=None, source_span=None,
           source_session_id=None, source_turn_at=None, derived_from=())
SourceSpan(start, end)
ResolutionMeta(schema_version, supersedes_ref=None, superseded_by_ref=None,
               supersession_reason=None, source_trust=None, confidence=None)
ResolutionState.CURRENT | .STALE | .SUPERSEDED | .UNKNOWN
```

Datetime-Normalisierung: #37 normalisiert auf **naive UTC** (`datetime` ohne tzinfo) und serialisiert als RFC3339 mit `Z`. #8 vergleicht `as_of` nach derselben Regel; `evidence/contract.py` hält dafür einen lokalen `_normalize_utc_datetime`-Helfer mit identischer Semantik (Repo-Präzedenz: `retrieval/contract.py` definiert seine Validatoren lokal, statt private Helfer fremder Pakete zu importieren). Die Zeit-Semantik selbst bleibt #37-Eigentum.

## Auflösungs- und Bewertungssemantik (festgenagelt)

### Public API (exakt)

```python
resolve_evidence(*, evidence, states=(), query=None, policy=None) -> EvidenceResolution
resolve_claims(*, claims, states=(), evidence=(), query=None, policy=None) -> ClaimResolution
query_decision_history(*, decisions, query, known_evidence_ids=None, known_claim_ids=None) -> DecisionHistoryResult
build_decision_replay(*, decisions, query, as_of, known_evidence_ids=None, known_claim_ids=None,
                      evidence_summaries=None, claim_summaries=None) -> DecisionReplay
detect_contradictions(*, bundle, rules=None, as_of) -> ContradictionScanResult
evaluate_freshness(*, bundle, policy=None, as_of) -> FreshnessReport
detect_scope_drift(*, bundle, policy, as_of) -> ScopeDriftReport
build_scope_drift_blocking(report) -> ScopeDriftBlocking
score_quality(*, scope_id, as_of, level="system", surfaces=(), dependency_edges=(),
              evidence_resolution=None, claim_resolution=None, decision_history=None,
              contradictions=None, freshness=None, scope_drift=None, policy=None) -> QualityAssessment
build_trust_summary(*, request, evidence_resolution=None, claim_resolution=None,
                    decision_history=None, contradictions=None, freshness=None,
                    scope_drift=None, quality=None, policy=None) -> TrustSummary
```

### Vokabulare (Core, in `contract.py`)

```text
EVIDENCE_STRENGTH_LEVELS = none, weak, moderate, strong, blocking_missing
EVIDENCE_STATUSES = active, revoked, unknown
CLAIM_STATUSES = unknown, proposed, supported, weakly_supported, disputed, invalidated
DECISION_STATUSES = unknown, proposed, accepted, parked, invalidated
SEVERITY_LEVELS = info, warning, blocking
FINDING_STATUSES = open, resolved, refreshed, replaced
QUALITY_GRADES = blocking, watch, weak, good
TRUST_LEVELS = strong, partial, insufficient
EVIDENCE_SUFFICIENCY_LEVELS = sufficient, partial, insufficient
CONTRADICTION_TYPES = claim_vs_evidence, decision_vs_evidence,
                      stale_decision_vs_new_evidence, cross_provenance_conflict
STALE_TYPES = source_hash_changed, source_deleted, validity_window_closed,
              dependency_edge_no_longer_observed, stale_context_package, stale_briefing
SCOPE_DRIFT_TYPES = path_out_of_scope, forbidden_surface_touched, runtime_surface_touched,
                     write_intent_without_authorization_ref, write_mode_without_authorization_ref,
                     domain_out_of_scope, issue_out_of_scope, unexpected_dependency_expansion
```

`stale` und `superseded` stehen in **keinem** gespeicherten Statusvokabular — sie sind abgeleitete `ResolutionState`-Werte.

### `ResolutionState`-Ableitung (Präzedenz `UNKNOWN > SUPERSEDED > STALE > CURRENT`)

| Bedingung | Zustand | `reason_code` |
|---|---|---|
| `temporal.known_at > as_of` | `UNKNOWN` | `not_yet_known` |
| `temporal.valid_from > as_of` | `UNKNOWN` | `not_yet_valid` |
| `temporal.valid_until <= as_of` | `STALE` | `validity_window_closed` |
| `superseded_by_ref` gesetzt, Ziel bekannt | `SUPERSEDED` | `superseded_by_ref` |
| `superseded_by_ref` gesetzt, Ziel unbekannt | `UNKNOWN` | `broken_supersession_chain` |
| Cross-Provenance-Konflikt | `UNKNOWN` | `cross_provenance_conflict` |
| sonst | `CURRENT` | `current` |

Ablieferung: `FreshnessReport.resolution_states: tuple[ResolutionStateEntry, ...]`; `ResolutionStateEntry` trägt `ref`, `entity_kind`, `resolution_state` (Wert aus #37), `reason_code`, `explanation`.

### Policy-Defaults (alle Zahlen ausschließlich hier)

| Policy | Default |
|---|---|
| `QualityPolicy.default()` | `dimension_weights` = alle sieben Dimensionen `1.0`; `grade_bands` = `blocking < 0.30`, `watch < 0.50`, `weak < 0.70`, `good >= 0.70`; `severity_penalties` = `blocking 0.50`, `warning 0.25`, `info 0.0`; `dependency_confidence_threshold` = `0.5` |
| `TrustPolicy.default()` | `component_weights` = evidence/claims/decisions je `1.0`; `level_thresholds` = `strong 0.80`, `partial 0.50`; `required_components` = `("evidence", "claims", "decisions")` |
| `FreshnessPolicy.default()` | `default_freshness_window_seconds` = `86400`; `expiry_grace_seconds` = `0`; `exempt_statuses` = `("resolved", "refreshed", "replaced")` |
| `ScopeDriftPolicy.default()` | `target_paths`/`allowed_domains`/`allowed_issues`/`forbidden_surfaces`/`protected_surface_types`/`write_like_operation_modes` = leer; `max_artifact_count` = `20`; `default_recommended_reads` = leer |
| `EvidenceResolutionPolicy.default()` | `acceptable_strengths` = `("moderate", "strong")`; `default_strength` = `"weak"` |
| `ClaimResolutionPolicy.default()` | `statuses_requiring_evidence` = `("supported", "weakly_supported")`; `blocking_statuses` = `("disputed", "invalidated")` |

`dependency_confidence_threshold = 0.5` ist eine Planentscheidung, die die Spec offenlässt: konservativer, generischer Wert; Claire nutzte ein String-Vokabular (`high/medium/low/unknown`) und wird ausschließlich über die Parity-Policy abgebildet.

## AC-Mapping (alle 10 ACs)

| AC | Source Behavior | Agent-Brain Component | Input | Output | RED Test | GREEN Evidence | Negative Control | Parity Evidence | Deferred Dependency |
|---|---|---|---|---|---|---|---|---|---|
| AC1 #37 Contract-GO | #37 kanonisiert Temporal-/Provenance-/Supersession-Semantik | `contract.py` komponiert #37 ohne Duplikation | `TemporalEnvelope`, `Provenance`, `ResolutionMeta` | Overlays mit `temporal`/`provenance`/`resolution_meta` | `test_evidence_contracts.py` | Overlays enthalten kein eigenes Zeit-/Provenance-/Supersession-Feld | kein persistiertes `resolution_state` | #37-PR #42, gemergt `3b23f75` | — |
| AC2 deterministische Zuordnung | Claire `claim_resolver`/`evidence_lookup` | `resolve_evidence`, `resolve_claims` | `EvidenceRef[]`, `ClaimRef[]`, Overlays | `EvidenceResolution`, `ClaimResolution` | `test_resolution.py` | stabile Ordnung, identische Ergebnisse bei reorder | unresolved refs, orphan overlays, missing evidence | `test_wave14_services_v1.py` (PORT) | — |
| AC3 #15-Contracts konsumieren | #15 `EvidenceRef`/`ClaimRef` | `contract.py`, `resolver.py` | #15-Typen | unverändert konsumierte Identität | `test_evidence_contracts.py` | `agent_brain.contracts.evidence` unverändert | kein v2-Bump, keine Zweitdefinition | `test_context_graph_contract.py` | — |
| AC4 #37-Semantik konsumieren | #37-Verträge | `contract.py`, `freshness.py`, `decisions.py` | #37-Typen | abgeleitete States, keine Duplikate | `test_temporal_semantics.py`, `test_supersession_semantics.py` | `known_at`/`valid_*` korrekt genutzt, `system_as_of` nie als Fact-Zeit | `not_yet_known`, `not_yet_valid`, dangling, Cycle | `test_temporal_contracts.py` (Referenz) | — |
| AC5 `source_trust` ≠ `confidence` | Claire trennt Trust/Confidence | `trust.py` | `ResolutionMeta.source_trust`, `.confidence` | `source_trust_assessment`, `confidence_assessment` | `test_source_trust_confidence_separation.py` | Änderung des einen ändert den anderen nicht | kein Kollabieren, kein Composite-Beitrag | `test_trust_threshold_contract.py` (nur Form-Vergleich) | — |
| AC6 Replay erklärt, autorisiert nicht | Claire `decision_replay_builder` | `build_decision_replay` | `DecisionRecord[]`, `as_of` | `DecisionReplay` | `test_decision_replay.py` | `authorization_implied` immer `False`, `limitations` nicht leer | keine Authority-Felder | `test_decision_replay_builder_v1/v2.py` (PORT) | — |
| AC7 Integrity sichtbar | Claire `contradiction_scan`, `stale_knowledge_scan`, `scope_drift_firewall` | `contradiction.py`, `freshness.py`, `scope_drift.py` | Bundles, `as_of` | Findings + Reports | `test_contradiction.py`, `test_freshness.py`, `test_scope_drift.py` | Findings materialisiert, nichts still gefiltert | blocking counts, override fehlt, kein Score-Boost | `test_contradiction_scan.py`, `test_stale_knowledge_scan.py`, `test_scope_drift_firewall.py` (PORT) | — |
| AC8 Trust-Sufficiency | Claire `trust_summary` | `trust.py` | Resultobjekte 1–4 | `TrustSummary` | `test_trust.py` | `strong`/`partial`/`insufficient` + `evidence_sufficiency` | fehlende Komponente ⇒ ≤ `partial` | `test_trust_summary.py` (PARITY ONLY) | — |
| AC9 Claire-Contracts abgedeckt | Slice-8-Testfläche der Claire-Baseline | `tests/evidence/` | neutrale Fixtures | PORT-/PARITY-Abdeckung | `test_claire_parity_policy.py` | Parity-Matrix vollständig klassifiziert | Claire-Zahlen nur in der Policy-Fixture | `docs/extraction/PARITY_GATES.md` | — |
| AC10 keine Produktsemantik | Claire-Produktanteile | gesamt | alle Core-Module | produktneutraler Core | `test_product_neutrality.py` | Wortliste-/Import-Scan grün | keine Claire-/CDB-/Trading-Begriffe, keine Host-Pfade | Slice-7-Präzedenz | — |

## Source→Target-Matrix (Slice 8, Charakterisierung nur)

| Claire-Fläche (Baseline `84b5e05`) | Entscheidung | Ziel in #8 |
|---|---|---|
| `claim_resolver.py` | MOVE | `resolver.py` → `resolve_claims` |
| `evidence_lookup.py` | MOVE | `resolver.py` → `resolve_evidence` |
| `claim_evidence_at_rest.py` (Struktur-/Metadata-Gate) | MOVE | `resolver.py` (Validierung) |
| `claim_evidence_at_rest.py` (DB-Pfad) | DEFER #10 | — |
| `claim_evidence_proof_runtime.py` / `_cli.py` | DEFER #10/#12 | — |
| `decision_history_query.py` | MOVE | `decisions.py` → `query_decision_history` |
| `decision_replay_builder.py` | MOVE | `decisions.py` → `build_decision_replay` |
| `contradiction_scan.py` (Finding-Modell) | MOVE | `contradiction.py` |
| `contradiction_scan.py` (3 generische Regeltypen) | MOVE | Default-`ContradictionRuleSet` |
| `contradiction_scan.py` (übrige Regeltypen) | DEFER #12/#13 | — |
| `contradiction_scan.py` (Override-Workflow) | DEFER #12 | — |
| `contradiction_cli.py` | DEFER #12 | — |
| `stale_knowledge_scan.py` (generische Typen) | MOVE | `freshness.py` |
| `stale_knowledge_scan.py` (`memory_ttl_expired`) | DEFER #11 | — |
| `stale_refresh_plan.py` | MOVE reduziert | `freshness.py` → `recommended_refresh` |
| `stale_context_cli.py` | DEFER #12 | — |
| `scope_drift_firewall.py` (Mechanik) | MOVE | `scope_drift.py` |
| `scope_drift_firewall.py` (Produktpolicy) | ADAPTER | `ScopeDriftPolicy` beim Consumer |
| `scope_drift_blocking.py` | MOVE | `scope_drift.py` → `build_scope_drift_blocking` |
| `scope_drift_cli.py` | DEFER #12 | — |
| `quality_scoring.py` (Mechanik, 7 Dimensionen) | MOVE | `quality.py` |
| `quality_scoring.py` (Memory-Dimension) | DEFER #11 | — |
| `quality_scoring_cli.py` | DEFER #12 | — |
| `trust_summary.py` (Mechanik, 3 Komponenten) | MOVE | `trust.py` |
| `trust_summary.py` (Operator-/Live-Policy) | DEFER #13 | — |
| `negative_controls.py` | MOVE nur Invariante | `test_no_authority_signals.py` |
| `negative_controls_matrix.py` | DEFER | späterer Write-Scope |
| `architect_signals.py` | DEFER | späterer Consumer |
| `drift_report.py` | MOVE reduziert | `scope_drift.py` |

## TDD Task Decomposition (independently reviewable)

### Task 1: #8 Contracts / Policies / Public Types

**Files**
- Create: `src/agent_brain/evidence/contract.py`, `src/agent_brain/evidence/__init__.py` (leere Public-Surface-Hülle, `__all__` folgt in Task 8)
- Modify: —
- Test: `tests/evidence/test_evidence_contracts.py`, `tests/evidence/test_public_surface.py` (nur Inventar-Teil)

**Interfaces**
- Consumes: `EvidenceRef`, `ClaimRef`, `TemporalEnvelope`, `Provenance`, `ResolutionMeta`, `ResolutionState`, `require_compatible_version`, `serialize_contract`, `canonical_hash`
- Produces: `EvidenceState`, `ClaimState`, `DecisionRecord`, `EvidenceQuery`, `ClaimQuery`, `DecisionQuery`, `DecisionReplayQuery`, `TrustRequest`, `EvidenceResolution`, `ClaimResolution`, `DecisionHistoryResult`, `DecisionReplay`, `ContradictionFinding`, `ContradictionScanResult`, `StaleFinding`, `ResolutionStateEntry`, `FreshnessReport`, `ScopeDriftFinding`, `ScopeDriftReport`, `ScopeDriftBlocking`, `QualityDimensionScore`, `QualityAssessment`, `TrustSummary`, `QualityPolicy`, `TrustPolicy`, `FreshnessPolicy`, `ScopeDriftPolicy`, `EvidenceResolutionPolicy`, `ClaimResolutionPolicy`, `EvidenceError` + 7 Unterklassen, alle Vokabulare

- [ ] RED: Schema-Familie und Major-Version jedes Typ-A-Contracts werden fail-closed abgelehnt (`require_compatible_version`).
- [ ] RED: `to_dict()`/`from_dict()`-Roundtrip erhält alle Felder; `from_dict` ignoriert unbekannte additive v1-Felder.
- [ ] RED: Overlays enthalten **kein** eigenes `known_at`/`valid_from`/`valid_until`/`system_as_of`/`source_trust`/`confidence`/`supersedes_ref`/`superseded_by_ref`/`source_hashes`-Feld; `Confidence`/`source_trust` stehen ausschließlich in `ResolutionMeta`.
- [ ] RED: Kein #8-Contract führt ein Feld namens `resolution_state`; `ResolutionState` wird ausschließlich als **Wert** in `ResolutionStateEntry` verwendet.
- [ ] RED: `EvidenceState`/`ClaimState`/`DecisionRecord` sind `frozen=True, slots=True`; Mutation wirft `FrozenInstanceError`.
- [ ] RED: `to_dict()` liefert JSON-sichere Primitive (Datetimes via #37-Serialisierung, Tupel als Listen).
- [ ] RED: `QualityPolicy.default()` liefert die in [Policy-Defaults](#policy-defaults-alle-zahlen-ausschließlich-hier) fixierten Zahlen; keine andere Policy führt score-relevante Zahlen.
- [ ] RED: Policy-Mappings werden read-only materialisiert (`MappingProxyType`); Änderungsversuch wirft.
- [ ] RED: `QualityPolicy` mit Gewicht außerhalb `[0,1]` oder Band außerhalb `[0,1]` wirft `QualityError`; `TrustPolicy` analog `TrustError`.
- [ ] RED belegen: fokussierter Test schlägt erwartet fehl (Assertion/Exception), kein Import- oder Syntaxfehler.
- [ ] GREEN: `contract.py` mit allen Typen, lokalen Validatoren (`_required_text`, `_optional_text`, `_text_tuple`, `_non_negative_int`, `_positive_int`, `_score`, `_normalize_utc_datetime`) und `to_dict`/`from_dict`.
- [ ] GREEN: `__init__.py` mit Modul-Docstring und zunächst leerem `__all__` (Surface-Export folgt in Task 8).
- [ ] Test: `test_evidence_contracts.py` fokussiert grün.
- [ ] Task-Suite (`tests/evidence/`) komplett grün.
- [ ] Ruff fokussiert + Gesamt-Ruff grün.
- [ ] Diff prüfen: nur `src/agent_brain/evidence/**` und `tests/evidence/**`.
- [ ] Commit: `feat: add slice 8 evidence contracts and policies`

### Task 2: Evidence / Claim Resolution

**Files**
- Create: `src/agent_brain/evidence/resolver.py`
- Modify: —
- Test: `tests/evidence/test_resolution.py`

**Interfaces**
- Consumes: `EvidenceRef`, `ClaimRef`, `EvidenceState`, `ClaimState`, `EvidenceQuery`, `ClaimQuery`, `EvidenceResolutionPolicy`, `ClaimResolutionPolicy`
- Produces: `resolve_evidence(...) -> EvidenceResolution`, `resolve_claims(...) -> ClaimResolution`

- [ ] RED: `resolve_claims` löst `ClaimRef.evidence_refs` gegen bekannte `EvidenceRef.evidence_id` auf; nicht auflösbare Refs erscheinen in `unresolved_evidence_refs`.
- [ ] RED: Claim mit Status `supported`/`weakly_supported` ohne auflösbare Evidence erscheint in `missing_evidence_claim_ids`.
- [ ] RED: Claim ohne `ClaimState` ⇒ Status `unknown`, Warnung `claim_without_state_overlay`, nie in einer positiven Bucket.
- [ ] RED: Overlay ohne passenden Ref ⇒ Warnung `orphan_evidence_state` / `orphan_claim_state`, nicht still verworfen.
- [ ] RED: Fehlender `EvidenceState` ⇒ Stärke aus `EvidenceResolutionPolicy.default_strength` (`weak`), nie `strong`.
- [ ] RED: Kein Ergebnis enthält `stale_evidence_ids`, `by_freshness` oder eine Alters-/Ablaufbewertung; die Resolver-Signaturen haben **kein** `as_of`.
- [ ] RED: Query-Modi matchen exakt; Substring-Match ist ausgeschlossen (`scope`/`source` treffen keine Präfixe).
- [ ] RED: Sortierung ist stabil über `temporal.known_at` + ID; undatierte Records stehen hinten; umgekehrte Eingabereihenfolge ändert das Ergebnis nicht.
- [ ] RED: Unbekannter Query-Modus, `limit` außerhalb `1..10000`, fehlender Pflicht-Selektor und Record ohne `evidence_id`/`claim_id` schlagen fail-closed fehl (`ResolutionError`).
- [ ] RED belegen: fokussierter Test schlägt erwartet fehl (Assertion/Exception), kein Import- oder Syntaxfehler.
- [ ] GREEN: `resolver.py` mit deterministischer Normalisierung, Overlay-Indexierung, Auflösung, Buckets, Warnungen und Limitations.
- [ ] Test: `test_resolution.py` fokussiert grün; Task-1-Suite bleibt grün.
- [ ] Ruff gesamt grün.
- [ ] Diff prüfen: nur `resolver.py` + Testdatei.
- [ ] Commit: `feat: add slice 8 evidence and claim resolution`

### Task 3: Decision History / Replay

**Files**
- Create: `src/agent_brain/evidence/decisions.py`
- Modify: —
- Test: `tests/evidence/test_decision_history.py`, `tests/evidence/test_decision_replay.py`, `tests/evidence/test_supersession_semantics.py`

**Interfaces**
- Consumes: `DecisionRecord`, `DecisionQuery`, `DecisionReplayQuery`, `DecisionHistoryResult`, `DecisionReplay`
- Produces: `query_decision_history(...) -> DecisionHistoryResult`, `build_decision_replay(...) -> DecisionReplay`

- [ ] RED: Bucketing folgt `ResolutionMeta`: `superseded_by_ref` gesetzt + Ziel bekannt ⇒ superseded; deklarierter Status `invalidated` ⇒ invalidated; sonst current.
- [ ] RED: Supersession-Kette folgt ausschließlich `superseded_by_ref`/`supersedes_ref`; **kein** Status-String-Ersatz, kein Rückschluss aus `status == "superseded"`.
- [ ] RED: Dangling `superseded_by_ref` (Ziel nicht in der Menge) ⇒ Bucket `unresolved` + Warnung `broken_supersession_chain`; **keine** stille Rückstufung auf `current`.
- [ ] RED: Supersession-Zyklus terminiert (keine Endlosschleife), Kettenlänge ist begrenzt durch die Recordmenge.
- [ ] RED: `supersession_reason` wird im Chain-Eintrag mitgeführt.
- [ ] RED: Fehlende `known_evidence_ids`/`known_claim_ids` ⇒ Warnung `resolution_inputs_not_provided`; „alles aufgelöst" wird nie behauptet.
- [ ] RED: Unaufgelöste Evidence-/Claim-Refs bleiben in `unresolved_evidence_refs`/`unresolved_claim_refs` sichtbar.
- [ ] RED: `build_decision_replay` ist deterministisch; `decision_chain_hash` ist über `canonical_hash` gebildet und **schließt `as_of` aus** — zwei Replays mit unterschiedlichem `as_of` bei gleicher Datenlage sind hashgleich.
- [ ] RED: Replay ist erklärend: `authorization_implied` ist immer `False`, `authorization_refs` werden nur durchgereicht, `limitations` ist nicht leer.
- [ ] RED: Sichtbarkeit und historischer Status bleiben getrennt: ein nicht sichtbarer Nachfolger ändert den Bucket nicht, er erzeugt die Sichtbarkeitswarnung.
- [ ] RED belegen: fokussierter Test schlägt erwartet fehl (Assertion/Exception), kein Import- oder Syntaxfehler.
- [ ] GREEN: `decisions.py` mit Normalisierung, Sortierung, Kettenaufbau, Bucketing, Replay-Aufbau, Hash und Explainability.
- [ ] Test: `test_decision_history.py`, `test_decision_replay.py`, `test_supersession_semantics.py` fokussiert grün.
- [ ] Task-Suite (`tests/evidence/`) komplett grün.
- [ ] Ruff gesamt grün.
- [ ] Diff prüfen: nur `decisions.py` + drei Testdateien.
- [ ] Commit: `feat: add slice 8 decision history and replay`

### Task 4: Contradiction + Cross-Provenance Conflict

**Files**
- Create: `src/agent_brain/evidence/contradiction.py`
- Modify: `src/agent_brain/evidence/resolver.py` (Konfliktgruppen-Erkennung), `src/agent_brain/evidence/contract.py` (nur falls `ContradictionBundle` die Stage-1-Resultate aufnehmen muss)
- Test: `tests/evidence/test_contradiction.py`, `tests/evidence/test_cross_provenance_conflict.py`

**Interfaces**
- Consumes: `ClaimRef`, `ClaimState`, `EvidenceRef`, `EvidenceState`, `DecisionRecord`, `EvidenceResolution`, `ClaimResolution`, `ContradictionBundle`, `ContradictionRuleSet`
- Produces: `ContradictionRule`, `ContradictionRuleSet`, `default_contradiction_rule_set()`, `detect_contradictions(...) -> ContradictionScanResult`

- [ ] RED: Kandidaten derselben `evidence_id` mit unterschiedlicher `provenance.source_ref` **und** ohne Supersession-Beziehung ergeben eine Konfliktgruppe; alle Kandidaten bleiben in der Resolution sichtbar, es existiert kein Gewinner-Feld.
- [ ] RED: `conflicting_evidence_ids` bzw. `conflicting_claim_ids` weisen die Gruppen aus.
- [ ] RED: Besteht eine explizite Supersession-Beziehung, entsteht **kein** Konflikt (der Vorgänger ist superseded, nicht konfliktär).
- [ ] RED: Gleicher `provenance.source_ref` und gleicher `source_hash` ⇒ kein Konflikt.
- [ ] RED: `cross_provenance_conflict` wird als Finding mit Severity `blocking` materialisiert und in `blocking_count` gezählt.
- [ ] RED: `claim_vs_evidence` (disputed/invalidated ⇒ blocking, stale ⇒ warning) und `decision_vs_evidence` (`requires_evidence=True` ohne auflösbare bzw. nur schwache Evidence) und `stale_decision_vs_new_evidence` treffen die in der Spec fixierten Severity-/Confidence-Werte.
- [ ] RED: Finding-IDs sind `canonical_hash(...)[:16]`, über Input-Reihenfolge stabil und eindeutig.
- [ ] RED: Die Detektorfunktionen enthalten **keine** Severity-/Confidence-Literale; alle Werte kommen aus der injizierten Regel. Ein AST-/Quelltext-Scan belegt das.
- [ ] RED: `detect_contradictions` mit ungültigem Bundle schlägt fail-closed fehl (`ContradictionError`); jeder Finding trägt `detected_at` aus `as_of`.
- [ ] RED belegen: fokussierter Test schlägt erwartet fehl (Assertion/Exception), kein Import- oder Syntaxfehler.
- [ ] GREEN: `resolver.py` (Konflikterkennung), `contradiction.py` (RuleSet, Default-Regeln, Detektoren, Findings, Report).
- [ ] Test: `test_contradiction.py`, `test_cross_provenance_conflict.py` fokussiert grün; Task-2-Suite bleibt grün.
- [ ] Ruff gesamt grün.
- [ ] Diff prüfen: nur `resolver.py`, `contradiction.py`, Testdateien.
- [ ] Commit: `feat: add slice 8 contradiction detection and conflict materialization`

### Task 5: Freshness + Scope Drift

**Files**
- Create: `src/agent_brain/evidence/freshness.py`, `src/agent_brain/evidence/scope_drift.py`
- Modify: —
- Test: `tests/evidence/test_freshness.py`, `tests/evidence/test_resolution_state_derivation.py`, `tests/evidence/test_temporal_semantics.py`, `tests/evidence/test_scope_drift.py`

**Interfaces**
- Consumes: `TemporalEnvelope`, `Provenance`, `ResolutionMeta`, `ResolutionState`, `GraphEdge`, `EvidenceRef`, `EvidenceState`, `DecisionRecord`, `FreshnessBundle`, `ScopeDriftBundle`, `FreshnessPolicy`, `ScopeDriftPolicy`
- Produces: `evaluate_freshness(...) -> FreshnessReport`, `detect_scope_drift(...) -> ScopeDriftReport`, `build_scope_drift_blocking(...) -> ScopeDriftBlocking`

- [ ] RED: `evaluate_freshness` wertet `valid_until <= as_of` ⇒ Stale-Finding `validity_window_closed` aus.
- [ ] RED: `system_as_of` löst **kein** Stale-Finding aus und wird nur als Snapshot-Metadatum geführt; ein `system_as_of` vor `known_at` ändert kein Ergebnis.
- [ ] RED: `known_at > as_of` ⇒ `UNKNOWN`/`not_yet_known`; `valid_from > as_of` ⇒ `UNKNOWN`/`not_yet_valid`; `valid_until <= as_of` ⇒ `STALE`/`validity_window_closed`; bekanntes Supersession-Ziel ⇒ `SUPERSEDED`; unbekanntes Ziel ⇒ `UNKNOWN`/`broken_supersession_chain`; Konflikt ⇒ `UNKNOWN`/`cross_provenance_conflict`; sonst ⇒ `CURRENT`.
- [ ] RED: Präzedenz ist `UNKNOWN > SUPERSEDED > STALE > CURRENT` (Doppelkonditionen-Fälle explizit getestet).
- [ ] RED: Fehlendes `valid_from`/`valid_until` erzeugt **keine** Stale-Behauptung, sondern eine sichtbare Limitation.
- [ ] RED: `dependency_edge_no_longer_observed` entsteht ausschließlich aus der Differenz erwarteter vs. aktuell beobachteter Edge-IDs; `GraphEdge.confidence` und `GraphEdge.inferred` sind **keine** Staleness-Proxies.
- [ ] RED: Kein `memory_ttl_expired`; kein Memory-Import in `freshness.py`.
- [ ] RED: `detect_scope_drift` verlangt `ScopeDriftPolicy` als Pflichtparameter; ohne Policy entsteht kein Ergebnis.
- [ ] RED: Pfadvergleich respektiert die Verzeichnisgrenze (`tools/surrealdb` trifft nicht `tools/surrealdb_extra`); Globs (`*`, `?`, `[`) werden explizit ausgewertet; leeres `target_paths` deaktiviert nur die Pfadregel.
- [ ] RED: Fehlende Autorisierungsreferenz ⇒ Finding `write_intent_without_authorization_ref` bzw. `write_mode_without_authorization_ref`; vorhandene Referenz ⇒ **kein** positives Autorisierungsfeld, nur das Finding entfällt.
- [ ] RED: `ScopeDriftBlocking` enthält nur `blocking`, `blocking_count`, `summary`, Artefakte, Findings, generische `recommended_actions`/`recommended_next_reads` — kein `operator_action`, keine `anti_actions`, kein autoritätsbehauptendes Feld.
- [ ] RED belegen: fokussierter Test schlägt erwartet fehl (Assertion/Exception), kein Import- oder Syntaxfehler.
- [ ] GREEN: `freshness.py` (Stale-Findings, `ResolutionState`-Ableitung als private Helper, Report), `scope_drift.py` (Drift-Findings, Blocking-Ausgabe).
- [ ] Test: alle vier Testdateien fokussiert grün; Task-3-Suite bleibt grün.
- [ ] Ruff gesamt grün.
- [ ] Diff prüfen: nur `freshness.py`, `scope_drift.py`, Testdateien.
- [ ] Commit: `feat: add slice 8 freshness and scope drift signals`

### Task 6: Quality Scoring

**Files**
- Create: `src/agent_brain/evidence/quality.py`
- Modify: —
- Test: `tests/evidence/test_quality.py`, `tests/evidence/test_conservative_defaults.py`

**Interfaces**
- Consumes: `EvidenceResolution`, `ClaimResolution`, `DecisionHistoryResult`, `ContradictionScanResult`, `FreshnessReport`, `ScopeDriftReport`, `GraphEdge`, `SurfaceState`, `QualityPolicy`
- Produces: `score_quality(...) -> QualityAssessment`

- [ ] RED: Genau sieben Dimensionen — `coverage`, `freshness`, `evidence`, `contradiction`, `dependency_confidence`, `decision_validity`, `scope_risk` — mit Score in `[0,1]`, Grade, Erklärung, `inputs_used`.
- [ ] RED: Zähldimensionen = erfüllte Kriterien / verfügbare Kriterien; `dependency_confidence` zählt nur `GraphEdge.confidence >= QualityPolicy.dependency_confidence_threshold`.
- [ ] RED: Invers-penalisierende Dimensionen nutzen `max(0, 1 - Σ policy.severity_penalties[severity])`; Report ohne aktive Findings ⇒ `1.0`; fehlender Report ⇒ Dimension **nicht verfügbar**.
- [ ] RED: Fehlende Dimension wird ausgelassen und als Limitation sichtbar — **kein** neutraler `0.5`-Ersatz.
- [ ] RED: Grade-Bänder kommen aus `QualityPolicy.default()`: `blocking < 0.30`, `watch < 0.50`, `weak < 0.70`, `good >= 0.70`.
- [ ] RED: Eine Dimension mit Grade `blocking` senkt einen Gesamt-Grade `weak`/`good` auf `watch`; `blocking` bleibt `blocking`.
- [ ] RED: NaN/Inf-Scores erzeugen keinen positiven Beitrag (Wert `0.0`, Warnung `non_finite_score`).
- [ ] RED: Gewichte sind gleich gewichtet; eine injizierte Policy ändert Gewichte ⇒ Ergebnis ändert sich ⇒ die Gewichte liegen in der Policy, nicht im Code.
- [ ] RED: Ein Quelltext-/AST-Scan belegt: keine score-relevante Zahl im Scoring-Algorithmus.
- [ ] RED: Freshness wird aus dem `FreshnessReport` **konsumiert**, nicht neu berechnet.
- [ ] RED belegen: fokussierter Test schlägt erwartet fehl (Assertion/Exception), kein Import- oder Syntaxfehler.
- [ ] GREEN: `quality.py` mit den sieben Dimensionen, Aggregation, Grade-Ableitung, Downgrade, Explainability.
- [ ] Test: `test_quality.py`, `test_conservative_defaults.py` fokussiert grün; Task-5-Suite bleibt grün.
- [ ] Ruff gesamt grün.
- [ ] Diff prüfen: nur `quality.py` + Testdateien.
- [ ] Commit: `feat: add slice 8 quality assessment`

### Task 7: Trust Summary

**Files**
- Create: `src/agent_brain/evidence/trust.py`
- Modify: —
- Test: `tests/evidence/test_trust.py`, `tests/evidence/test_source_trust_confidence_separation.py`

**Interfaces**
- Consumes: `TrustRequest`, `EvidenceResolution`, `ClaimResolution`, `DecisionHistoryResult`, `ContradictionScanResult`, `FreshnessReport`, `ScopeDriftReport`, `QualityAssessment`, `TrustPolicy`
- Produces: `build_trust_summary(...) -> TrustSummary`

- [ ] RED: Genau drei Komponenten — `evidence`, `claims`, `decisions`; **keine** Memory-Komponente, kein `memory_component_enabled`, kein Memory-Import.
- [ ] RED: `composite_score` = gewichtetes Mittel der verfügbaren Komponenten; Gewichte aus `TrustPolicy` (Default: je `1.0`).
- [ ] RED: `trust_level` ∈ `strong`/`partial`/`insufficient`; Schwellen aus `TrustPolicy.default()` (`strong 0.80`, `partial 0.50`).
- [ ] RED: Fehlende Pflichtkomponente ⇒ höchstens `partial`; alle fehlen ⇒ `insufficient`; `TrustPolicy.required_components` defaultet auf alle drei.
- [ ] RED: Blocking Findings (blocking-missing Evidence, missing/disputed/invalidated Claims, unaufgelöste Decision-Refs, blockierende Contradiction-/Scope-Findings) erzwingen `insufficient` und bleiben sichtbar.
- [ ] RED: `evidence_sufficiency` ∈ `sufficient`/`partial`/`insufficient` wird unabhängig vom Gesamtscore ausgewiesen.
- [ ] RED: `source_trust_assessment` und `confidence_assessment` werden getrennt ausgewiesen; Änderung von `source_trust` ändert `confidence_assessment` **und** `composite_score` nicht (und umgekehrt).
- [ ] RED: Fehlender `source_trust`/`confidence` gilt als *nicht bewertet*, nicht als niedriger Wert.
- [ ] RED: `assessed_at` wird aus `QualityAssessment.scored_at` übernommen; ohne Quality-Assessment ist er `None`; Trust erzeugt keine eigene Uhr.
- [ ] RED: `authorization`-ähnliche Felder kommen im Ergebnis nicht vor; `limitations` ist nicht leer.
- [ ] RED belegen: fokussierter Test schlägt erwartet fehl (Assertion/Exception), kein Import- oder Syntaxfehler.
- [ ] GREEN: `trust.py` mit Komponentenbewertung, Composite, Level-Ableitung, Sufficiency, getrennten Trust-/Confidence-Auswertungen, Blocking-Findings, Limitations.
- [ ] Test: `test_trust.py`, `test_source_trust_confidence_separation.py` fokussiert grün; Task-6-Suite bleibt grün.
- [ ] Ruff gesamt grün.
- [ ] Diff prüfen: nur `trust.py` + Testdateien.
- [ ] Commit: `feat: add slice 8 trust summary`

### Task 8: Neutral E2E / Public Surface / Parity / Docs

**Files**
- Create: `tests/evidence/test_e2e.py`, `tests/evidence/test_determinism.py`, `tests/evidence/test_product_neutrality.py`, `tests/evidence/test_no_authority_signals.py`, `tests/evidence/test_claire_parity_policy.py`, `tests/fixtures/evidence/*`
- Modify: `src/agent_brain/evidence/__init__.py` (vollständige `__all__`), `docs/START_HIER.md`, `docs/DATENFLUESSE.md`, `docs/contracts/README.md`
- Test: alle Dateien unter `tests/evidence/`

**Interfaces**
- Consumes: alle Stufen 1–5, `agent_brain.contracts` (#15 + #37)
- Produces: stabile öffentliche Surface `agent_brain.evidence.__all__`, neutrale Fixtures, aktualisierte Doku

- [ ] RED: E2E über neutrale Fixtures: #15-Refs → #8-Overlays → Resolution → Decisions → Integrity → Quality → Trust; Ergebnis deterministisch.
- [ ] RED: Umgekehrte Eingabereihenfolge und zwei identische Läufe ergeben identische Ergebnisse inklusive IDs, Hashes und Buckets.
- [ ] RED: Produktneutralitäts-Scan über alle Core-Module: keine Produkt-/Markt-/Freigabe-/Umgebungsbegriffe, keine Env-Präfixe, keine Claire-/Anbieter-/Produktnamen, keine Host-Pfade.
- [ ] RED: Import-Scan: kein DB-/Netzwerk-Client, kein SurrealQL, kein `urllib`/`requests`/`httpx`/`socket`, kein `subprocess`, kein Memory-Import, kein `agent_brain.core.time`-Import in `agent_brain.evidence`.
- [ ] RED: Kein autoritätsbehauptendes Resultfeld (Liste: `approved`, `approved_by`, `go`, `go_token`, `live_go`, `human_go`, `trading_allowed`, `authorization_granted`, `permission_granted`, `release_approved`, `execution_allowed`).
- [ ] RED: `test_public_surface.py` prüft `__all__` exakt gegen das in Task 1 definierte Inventar; jeder Typ ist importierbar und trägt bei Typ A `schema_version`.
- [ ] RED: `test_claire_parity_policy.py` lädt `tests/fixtures/evidence/claire_parity_policy.v1.json`, injiziert die Policy und belegt, dass der neutrale Mechanismus die veröffentlichten Claire-Werte reproduziert (Grade-Bänder, Severity-Penalties, Trust-Level). Die Fixture ist die einzige Fundstelle Claire-spezifischer Zahlen im Repo-Teilbaum.
- [ ] RED belegen: fokussierter Test schlägt erwartet fehl (Assertion/Exception), kein Import- oder Syntaxfehler.
- [ ] GREEN: `__init__.py` exportiert die stabile Surface; Fixtures committed; Doku in `docs/START_HIER.md`, `docs/DATENFLUESSE.md` (Slice-8-Datenfluss) und `docs/contracts/README.md` (Producer-/Consumer-Richtung) ergänzt.
- [ ] Test: gesamte `tests/evidence/`-Suite grün; Volle Suite grün.
- [ ] Finale Gates: `python -m pip install -e ".[dev]"`, `python -m ruff check .`, `python -m pytest tests/evidence/ -q`, `python -m pytest -q`, `git diff --check`.
- [ ] Diff prüfen: nur `src/agent_brain/evidence/**`, `tests/evidence/**`, `tests/fixtures/evidence/**` und die drei Doku-Dateien.
- [ ] Commit: `feat: complete neutral slice 8 evidence and trust pipeline`

## Negative Controls (Katalog)

Jeder Eintrag ist einem Test in `tests/evidence/` zugeordnet und muss RED→GREEN belegt sein.

| Negativkontrolle | Test |
|---|---|
| leere Eingaben (keine Evidence/Claims/Decisions/Findings) | `test_conservative_defaults.py` |
| doppelte IDs (zwei Records mit derselben ID) | `test_resolution.py`, `test_determinism.py` |
| umgekehrte Eingabereihenfolge | `test_determinism.py` |
| unbekannte Referenzen (`evidence_refs` ohne passenden Ref) | `test_resolution.py` |
| orphan Overlays (State ohne Ref) | `test_resolution.py` |
| fehlerhafte Schemata (falsche Familie, falsche Major-Version) | `test_evidence_contracts.py` |
| `NaN`, `+Inf`, `-Inf` in Scores | `test_quality.py`, `test_conservative_defaults.py` |
| fehlende Zeitstempel | `test_temporal_semantics.py` |
| zukünftiges `known_at` | `test_resolution_state_derivation.py` |
| ungültiges Gültigkeitsfenster (`valid_until <= valid_from`) | bereits durch #37 fail-closed — `test_temporal_semantics.py` belegt, dass #8 die Ableitung **nicht** umgeht |
| dangling Supersession | `test_supersession_semantics.py` |
| Supersession-Zyklus | `test_supersession_semantics.py` |
| Cross-Provenance-Konflikte | `test_cross_provenance_conflict.py` |
| unbekannter Status | `test_conservative_defaults.py` |
| fehlende Policy | `test_scope_drift.py` (`ScopeDriftPolicy` Pflicht), `test_quality.py` (Default greift) |
| versteckte Wall Clock | `test_product_neutrality.py` (kein Clock-Import, kein `now()`-Aufruf) |
| dict-/set-Nondeterminismus | `test_determinism.py` |
| absolute Host-Pfade | `test_product_neutrality.py` |
| Netzwerknutzung | `test_product_neutrality.py` |
| DB-Nutzung | `test_product_neutrality.py` |
| Memory-Importe | `test_product_neutrality.py` |
| Claire-/CDB-Importe | `test_product_neutrality.py` |
| autoritätsähnliche Output-Felder | `test_no_authority_signals.py` |

## Validation Plan

- `python -m pip install -e ".[dev]"`
- `python -m ruff check .`
- `python -m pytest tests/evidence/ -q`
- `python -m pytest -q`
- `git diff --check`
- Product-Neutrality-Scan (Wortliste + Import-Scan) grün
- No-Network-/No-DB-Scope-Gate grün
- Determinismus: zwei identische Läufe ⇒ identische Ergebnisse; Input-Reorder ⇒ identische Ergebnisse
- Claire-Parity-Matrix gegen `docs/extraction/PARITY_GATES.md` (Slice-8-Gate) und `docs/extraction/COMPONENT_OWNERSHIP.md` (§ 2.7) vollständig abgebildet
- AC-Mapping: alle 10 Live-ACs des Issue #8 mit Task- und Test-Evidenz belegt
- Full diff review
- Exact-head CI auf dem tatsächlichen PR-Head
- Review Threads prüfen
- Post-Merge CI

**Keine erwartete Testanzahl hart codieren.**

## PR/Merge/Post-Merge Gates

- Branch off dem bei Ausführungsstart aktuellen `main`; kein direkter Push auf `main`
- Diff gegen Issue #8 prüfen
- Required Checks grün vor Merge
- Exact-head SHA nach jeder Änderung neu validieren
- Keine offenen relevanten Review Threads
- Nach Merge `main` und Post-Merge-CI live verifizieren
- Issue #8 ACs **erst** nach live verifiziertem Merge und vollständig belegter Acceptance abhaken
- Issue #8 erst danach schließen

**Zielzustand nach vollständiger Umsetzung:** `DONE_MERGED_CLOSED`. Dieser Plan führt davon jetzt nichts aus.
