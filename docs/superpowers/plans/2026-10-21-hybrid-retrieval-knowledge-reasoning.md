# [SLICE 7] Hybrid Retrieval und Knowledge Reasoning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Issue #7 [SLICE 7] — produktneutrale Hybrid-Retrieval- und Knowledge-Reasoning-Komponente auf Basis stabiler #15-Source-/Index-Verträge und reproduzierbarer #16-Knowledge-Fixtures. Keine Claire-Produktlogik im Core, keine SurrealDB-Runtime, keine #8-/#10-Semantik.

**Architecture:** Neuer Layer `src/agent_brain/retrieval/` konsumiert `agent_brain.contracts` (IndexRecord, GraphEdge, ArtifactRef, RepositorySource, EvidenceRef, ClaimRef) und `agent_brain.knowledge` (KnowledgeSnapshot). In-Memory-Default, read-only, side-effect-free. Keine DB, kein Netzwerk, kein Wall-Clock im Ranking.

**Tech Stack:** Python >= 3.12, Standardbibliothek, pytest, Ruff. Keine neuen Runtime-Dependencies.

**Spec:** Issue #7 (OPEN, 7 ACs) — `docs/START_HIER.md` — `docs/DATENFLUESSE.md` — `docs/extraction/COMPONENT_OWNERSHIP.md` (Slice-7-MOVE-Flächen: impact_radar, stop_resolver, graph_vector_proof_cli, hybrid_retrieval_ranking als Charakterisierung nur) — `docs/extraction/PARITY_GATES.md` (Slice-7-Parity-Gate-Tests).

## Global Constraints

1. **Retrieval läuft ohne Claire-Import** — kein `jannekbuengener/Claire_de_Binare`-Pfad, kein Trading-Domain, kein Repo-Root im Core.
2. **Deterministische Gesamt-Sortierung** — totaler Sortierschlüssel aus stabilen IDs/Hashes, nie von dict-/set-/filesystem-/DB-Reihenfolge abhängig.
3. **Konservative Fallbacks** — fehlender/ungültiger Signal → Faktor 0.0 (nicht positiv abgeleitet), nie Trust aus fehlender Evidence.
4. **#8-Grenze sauber** — keine Claim-Resolution, keine Trust-Stufen, keine Contradiction/Stale/Scope-Drift/Quality-Engine; #7 liest nur vorhandene EvidenceRef/ClaimRef-Metadaten als Signal.
5. **#10-Grenze sauber** — kein SurrealDB-Client, kein SurrealQL, keine Connection/Namespace/Auth; testbar über KnowledgeSnapshot + In-Memory + Fixtures.
6. **Required Reads produktneutral** — über `RequiredReadsProfile`/`resolve_required_reads` (existierender #6-Contract), keine Claire-Dateilisten im Core.
7. **Stop Resolver generisch** — `PolicyHook.evaluate()` → `PolicyDecision(allowed=False)` = STOP (konservativer kein-Ergebnis- bzw. begrenzter Modus, keine Trading-/Live-GO-Autorität).
8. **Impact Radar annotierend** — Graph-Nachbarschaftssignal pro Kandidat, keine Decision/Trust-Semantik.
9. **Explainability strukturiert** — pro Candidate: Gesamtscore, Faktoren, Rohwert, normalisierter Wert, Gewicht, Beitrag, fehlende Faktoren, Fallbacks, Source-/Graph-Refs.
10. **Test-first RED→GREEN**, Ruff clean, statische Fixtures unter `tests/fixtures/retrieval/`.

## Review Focus

- **Equal-score / reordered input:** totaler Tie-Break muss dieselbe Reihenfolge liefern, unabhängig von Input-, Edge-, dict- oder set-Reihenfolge.
- **Missing / malformed signals:** fehlende, NaN-, Inf- oder unbekannte Faktoren dürfen keinen positiven Beitrag erzeugen; Default bleibt 0.0.
- **Graph corruption:** dangling edges und Zyklen dürfen weder Crash noch unbounded traversal noch künstlichen Score-Boost verursachen.
- **Required-read / stop boundary:** fehlende Required Reads und `PolicyDecision(allowed=False)` müssen konservativ und produktneutral behandelt werden.
- **Forbidden runtime coupling:** Retrieval-Core darf weder SurrealDB/Netzwerk noch Claire-/Trading-/Host-Pfad-Abhängigkeiten einführen.

---

## Exact File Map

### Create

| Datei | Zweck |
|---|---|
| `src/agent_brain/retrieval/contract.py` | `RetrievalQuery`, `RetrievalCandidate`, `RetrievalResult`, `RankingFactor`, `RankingExplanation`, `RetrievalPolicy`, `RetrievalStop`, `RetrievalImpact` |
| `src/agent_brain/retrieval/ranking.py` | Deterministischer hybrider Ranker, Score-Komposition, Tie-Breaking, Faktor-Normalisierung |
| `src/agent_brain/retrieval/graph_signals.py` | Graph-/Struktur-Signale aus `GraphEdge` (Edge-Types, Richtung, dangling, Zyklen, Traversal-Grenze) |
| `src/agent_brain/retrieval/required_reads.py` | Required-Reads-Integration über `RequiredReadsProfile` (produktneutral, keine Dateihardcodes) |
| `src/agent_brain/retrieval/stop_resolver.py` | Stop-Auflösung über `PolicyHook` → `PolicyDecision` (fail-closed) |
| `src/agent_brain/retrieval/impact_radar.py` | Impact-Radar-Mechanik (Input: Query+Candidates+Graph, Output: annotierte Kandidaten) |
| `src/agent_brain/retrieval/retriever.py` | End-to-End-Orchestrierung (collect → rank → explain → stop/impact) |
| `tests/retrieval/test_retrieval_contract.py` | Contract-RED (Schema, Serialisierung, Versionierung) |
| `tests/retrieval/test_ranking_determinism.py` | Determinismus, Reproduzierbarkeit, kein Wall-Clock |
| `tests/retrieval/test_tie_breaking.py` | Totaler Sortierschlüssel, Negative Controls (Input-Reorder, Equal Scores) |
| `tests/retrieval/test_graph_signals.py` | Graph-Signale, dangling edges, Zyklen, Traversal-Limit |
| `tests/retrieval/test_required_reads_integration.py` | Required-Reads über Profile, produktneutral |
| `tests/retrieval/test_stop_resolver.py` | Stop via PolicyDecision, harter Abbruch vs. begrenzter Modus |
| `tests/retrieval/test_impact_radar.py` | Impact-Annotation, fehlende Signale konservativ |
| `tests/retrieval/test_conservative_defaults.py` | Missing/NaN/Inf/leere Query/zero candidates/duplicates |
| `tests/retrieval/test_product_neutrality.py` | Keine Claire-/Trading-/Host-Pfade, kein DB/Netzwerk |
| `tests/fixtures/retrieval/neutral_index.neutral.v1.json` | Neutrale IndexRecord-Fixture |
| `tests/fixtures/retrieval/neutral_edges.neutral.v1.json` | Neutrale GraphEdge-Fixture |

### Modify

| Datei | Änderung |
|---|---|
| `src/agent_brain/retrieval/__init__.py` | Public Surface exportieren (kein Verhalten) |
| `docs/START_HIER.md` | Abschnitt Retrieval / Knowledge Reasoning (Slice 7) ergänzen |
| `docs/DATENFLUESSE.md` | Retrieval-Datenfluss-Mermaid ergänzen |

### Tests (Fokus-Suite)
`tests/retrieval/` (siehe oben), alle gegen neutrale Fixtures aus `#16` (`knowledge_snapshot.neutral.v1.json`) plus neue Retrieval-Fixtures.

## Ranking-Semantik (festgenagelt)

Jeder Faktor: Range `[0,1]`, Default `0.0` bei missing/malformed/NaN/Inf/unknown source, Normalization deterministisch, Gewichtung über `RetrievalPolicy` (injizierbar, Defaults definiert).

| Factor | Quelle | Range | Default | Missing Behavior | Weight | Tie-break |
|---|---|---|---|---|---|---|
| lexical | IndexRecord Text/Attribute | [0,1] | 0.0 | 0.0 | konfiguriert | record_id |
| semantic | Vector-Stub (optional, #10 später) | [0,1] | 0.0 | 0.0 (Deferred bis #10) | konfiguriert | record_id |
| graph | GraphEdge confidence/traversal | [0,1] | 0.0 | 0.0 (dangling/zyklus) | konfiguriert | record_id |
| source_priority | SourcePriority rank | [0,1] | 0.0 (unbekannt) | 0.0 | konfiguriert | record_id |
| evidence_provenance | EvidenceRef aanwezigheid | [0,1] | 0.0 | 0.0 | konfiguriert | record_id |

Gesamtscore = gewichtete Summe (deterministisch, reproduzierbar, erklärbar). Tie-Breaker: `(-score, record_id asc, edge_id asc)` — stabil über IDs/Hashes.

Negative Controls (eigene Tests): empty query, whitespace-only, zero candidates, duplicates, equal scores, input reordering, edge reordering, dangling edge, graph cycle, malformed score, NaN/Inf, missing source/provenance/evidence, invalid/unknown factor, unsupported record type, required-read missing, host path in fingerprint, wall clock in ranking, dict/set iteration nondeterminism, fixture without Claire, attempted DB/network access.

## Ac-Mapping (alle 7 ACs)

| AC | Source Behavior | Agent-Brain Component | Input | Output | RED Test | GREEN Evidence | Negative Control | Parity Evidence | Deferred Dependency |
|---|---|---|---|---|---|---|---|---|---|
| AC1 | Retrieval Core ohne Claire-Import | retrieval/retriever.py + contract.py | RetrievalQuery (neutral) | RetrievalResult | test_product_neutrality | Core importbar ohne Claire, keine Claire-Pfade | Import von Claire-Modulen schlägt fehl | Parity_GATES Slice 7 | keine |
| AC2 | Ranking deterministisch + erklärbar | retrieval/ranking.py | Candidates + Policy | RankingExplanation pro Candidate | test_ranking_determinism | Gleicher Input → gleicher Score + Explanation | Wall-Clock / Host-Pfade im Score | test_hybrid_retrieval_ranking | keine |
| AC3 | Konsumiert #15 Contracts | retrieval/contract.py + ranking.py | IndexRecord, GraphEdge, ArtifactRef | typisierte Kandidaten | test_retrieval_contract | Contract-Familien index-record/v1, graph-edge/v1, artifact-ref/v1 | Fremde Schema-Familien abgelehnt | test_index_contracts | keine |
| AC4 | Neutrale #16-Fixture reicht | tests/fixtures/retrieval/* + knowledge_snapshot.neutral.v1.json | KnowledgeSnapshot | RetrievalResult | test_neutral_fixture_retrieval | Reproduzierbare Tests ohne Claire/DB | Fehlende Fixture → Test-Fehler | test_knowledge_refresh_report | keine |
| AC5 | Claire Required Reads nur über Profile/Adapter | retrieval/required_reads.py | RequiredReadsProfile + resolve_required_reads | RequiredRead-Auswirkung auf Ranking/Stop | test_required_reads_integration | Keine Claire-Dateilisten im Core | Hardcodierter Claire-Pfad | test_context_required_reads | keine (existierender #6-Contract) |
| AC6 | Fehlende Evidence → konservativ | retrieval/ranking.py + stop_resolver.py | fehlende/malformed Signale | Score 0.0 / Stop / konservativer Default | test_conservative_defaults | Kein positiver Score aus fehlender Evidence | NaN/Inf wird nicht positiv | test_negative_controls_regression | #8 (Trust) DEFERRED_TO |
| AC7 | Claire-Retrieval-Regressionen portiert/Parity | tests/retrieval/* + docs Mapping | Claire Parity-Gate-Tests | Portierte Agent-Brain-Tests | test_tie_breaking + test_graph_signals | Claire-RED-Tests 3486/3487 abgedeckt | Keine 1:1-Klassenübernahme | PARITY_GATES.md Slice 7 | #14 Parity/Dual Run |

## Source→Target-Matrix (Slice 7, Charakterisierung nur)

| Claire Source | Verhalten | Abhängigkeiten | Produktneutral? | Klassifikation | Agent-Brain Target | Parity Evidence | Deferred Dependency |
|---|---|---|---|---|---|---|---|
| `hybrid_retrieval_ranking.py` | Hybrid Ranking + Score | core.clock (CDB), Trading-Guardrail | nein (Clock/Trading entfernt) | MOVE → GENERALIZE | retrieval/ranking.py | test_hybrid_retrieval_ranking | keine |
| `context_impact_radar.py` | Impact-Auswertung | Claire Control Room | nein | MOVE → GENERALIZE | retrieval/impact_radar.py | test_context_impact_radar | keine |
| `context_stop_resolver.py` | Stop/Readiness | Claire LR/Echtgeld-Texte | nein | MOVE → GENERALIZE | retrieval/stop_resolver.py | test_context_stop_resolver | keine |
| `graph_vector_proof_cli.py` | Graph/Vector Proof | SurrealDB | nein | MOVE → FIXTURE ONLY | tests/fixtures/retrieval/neutral_edges.*.json | test_graph_vector_proof_cli | #10 (SurrealDB) |

## TDD Task Decomposition (independently reviewable)

### Task 1: Retrieval Contracts / Policy / Explanation
- [ ] RED: Contract-Schema-Ablehnung, Versionierung, Serialisierung
- [ ] GREEN: `contract.py` mit allen Typen + `to_dict`/`from_dict`
- [ ] Test: `test_retrieval_contract.py`
- [ ] Ruff + fokussierte Tests
- [ ] Commit: `feat: add retrieval contracts and explanation model`

### Task 2: Deterministic Candidate Collection
- [ ] RED: Sammlung aus IndexRecord/GraphEdge/ArtifactRef, dedupliziert, sortiert stabil
- [ ] GREEN: `retriever.py` collect-Phase
- [ ] Test: `test_retrieval_contract.py` (Teil), Produktneutralität
- [ ] Ruff + fokussierte Tests
- [ ] Commit: `feat: add deterministic retrieval candidate collection`

### Task 3: Hybrid Ranking + Tie Breaking
- [ ] RED: Zwei Builds identisch, Tie-Break total, kein Wall-Clock
- [ ] GREEN: `ranking.py` (gewichtete Summe, Tie-Breaker `(-score, record_id)`)
- [ ] Test: `test_ranking_determinism.py`, `test_tie_breaking.py`
- [ ] Ruff + fokussierte Tests
- [ ] Commit: `feat: add deterministic hybrid retrieval ranking`

### Task 4: Graph Signals + Impact Radar
- [ ] RED: dangling edge, Zyklus, Traversal-Limit, Impact-Annotation
- [ ] GREEN: `graph_signals.py`, `impact_radar.py`
- [ ] Test: `test_graph_signals.py`, `test_impact_radar.py`
- [ ] Ruff + fokussierte Tests
- [ ] Commit: `feat: add retrieval graph signals and impact radar`

### Task 5: Required Reads + Stop Resolver
- [ ] RED: RequiredReadsProfile-Integration, PolicyDecision allowed=False → STOP
- [ ] GREEN: `required_reads.py`, `stop_resolver.py`
- [ ] Test: `test_required_reads_integration.py`, `test_stop_resolver.py`
- [ ] Ruff + fokussierte Tests
- [ ] Commit: `feat: add required reads and stop resolver`

### Task 6: Neutral End-to-End Fixture / Parity / Public Surface / Docs
- [ ] RED: Fixture-basierter E2E-Run, Parity-Mapping, Produktneutralität
- [ ] GREEN: `retriever.py` orchestriert alle Tasks, `__init__.py` exportiert, Fixtures committed, Docs ergänzt
- [ ] Test: `test_product_neutrality.py`, `test_conservative_defaults.py`, E2E gegen `knowledge_snapshot.neutral.v1.json`
- [ ] Ruff + fokussierte Tests
- [ ] Finale Gates: `python -m pip install -e ".[dev]"`, `python -m ruff check .`, `python -m pytest -q`
- [ ] Commit: `feat: complete neutral hybrid retrieval slice`

## Validation Plan

- `python -m pip install -e ".[dev]"`
- `python -m ruff check .`
- `python -m pytest -q`
- Fokussierte Retrieval-Suite (`tests/retrieval/`)
- Determinism tests (zwei Runs, identisch)
- Neutrality test (keine Claire/Trading/Host-Pfade, kein DB/Netzwerk)
- No-network/no-DB scope gate (Import-Test blockiert SurrealDB)
- Claire parity mapping (`PARITY_GATES.md` Slice 7 + RED 3486/3487)
- Full diff review
- AC mapping (alle 7 ACs abgedeckt)
- Exact-head CI auf dem tatsächlichen PR-Head
- Review Threads
- Post-Merge CI

## PR/Merge/Post-Merge Gates

- Branch off dem bei Ausführungsstart aktuellen `main`; kein direkter Push auf `main`
- Diff gegen Issue #7 prüfen
- Required Checks grün vor Merge
- Exact-head SHA nach jeder Änderung neu validieren
- Keine offenen relevanten Review Threads
- Nach Merge `main` und Post-Merge-CI live verifizieren
- Issue erst nach live verifiziertem Merge und vollständiger Acceptance schließen
