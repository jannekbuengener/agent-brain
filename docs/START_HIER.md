# Start hier — Agent Brain

## Was ist Agent Brain?

Agent Brain ist das gemeinsame Kontext- und Wissenssystem für KI-Agenten. Es entscheidet nicht selbst, **was** ein Produkt tun darf. Es hilft Agenten, den aktuellen Zustand eines Projekts korrekt zu verstehen, relevante Zusammenhänge wiederzufinden und Aussagen mit Evidence zu belegen.

Das System wurde aus dem Context-/Agent-Brain von Claire de Binare extrahiert und als eigenständiges Repository generalisiert. Die ursprüngliche Extraction-/Consumerization-Roadmap ist abgeschlossen; spätere Arbeit entsteht consumer-driven aus realem Bedarf.

## Die wichtigste Trennung

- **GitHub / jeweiliges Repo** = aktuelle Wahrheit.
- **Agent Brain** = Kontext, Retrieval, Evidence, Memory, Trust.
- **Agent Workforce** = Rollen, Zuständigkeiten und Agentenführung.
- **Claire de Binare** = Trading-Core und Claire-spezifische Policies.

Agent Brain liefert Kontext, aber keine Produkt-, Trading- oder Live-Autorität.

## Wo beginne ich?

1. [Portable Foundation](foundation/README.md) — produktneutrale Core-Primitiven und ihre Grenzen.
2. [Gemeinsame Contracts](contracts/README.md) — versionierte Repository-, Index-/Graph- und Evidence-/Claim-Datenverträge.
3. [Context Package und Briefing Core](context/README.md) — deterministische Context Packages, Required Reads, Self-Explanation, Validation und Briefing.
4. [Repository Ingestion und Connectors](connectors/README.md) — read-only, produktneutrale lokale Ingestion und #15-Ausgaben.
5. [Entwicklungsbaseline](DEVELOPMENT.md) — Installation, Tests und die aktuell erlaubten Modulgrenzen.
6. [Externe Referenzdokumentation](external-docs/index.md) — `P0`/`P1` markieren aktuell belegte Referenzen mit Repo-Evidence; `P2` ist geparkt/reference-only und keine Runtime-/Dependency-Aussage.
7. [Datenflüsse](DATENFLUESSE.md) — visuelle Mermaid-Erklärung des Systems.
8. [Extraction Canon](extraction/README.md) — was aus Claire wohin gehört und wie bestehender State behandelt wurde.
9. [Repository Adoption How-to](extraction/REPOSITORY_ADOPTION_HOWTO.md) — wiederverwendbares Verfahren für weitere Repositories: Live-State, Canon-Audit, Ownership, State, Parity, Adoption und Closeout.
10. [Extraction Design](superpowers/specs/2026-10-20-agent-brain-extraction-design.md) — historische Zielarchitektur und Migrationslogik.
11. [Epic #2](https://github.com/jannekbuengener/agent-brain/issues/2) — abgeschlossene Extraction-/Consumerization-Authority.

## Slice #9 — Repository Ingestion / Connectors (implementiert)

Der read-only, produktneutrale Ingestionskern ist implementiert. Er liest explizit profilierte lokale Repositories und erzeugt deterministische #15-Ausgaben für den Knowledge-Build #16:

- [Source → Target Matrix](extraction/SLICE_5_SOURCE_TARGET_MATRIX.md) — Claire-Verhalten: übernehmen, generalisieren, Adapter/Stay/Defer.
- [Acceptance / Parity / Risk Matrix](extraction/SLICE_5_ACCEPTANCE_PARITY_MATRIX.md) — jedes AC mit Beweis und Negative Controls.
- [Implementation Plan](superpowers/plans/2026-10-20-repository-ingestion-connectors.md) — TDD-/Task-Reihenfolge.
- [SurrealDB Reference Landscape](external-docs/surrealdb-reference-landscape.md) — Reuse-/Research-Routing; keine automatische Runtime-Dependency.

Die Entscheidungen über Claire-vs-Core, DB-Writes, Repo-Identität und SurrealDB-Aktivierung sind damit festgelegt; ein Consumer folgt dem Connectors-README und den #15-Verträgen.

## Slice #6 — Knowledge Build / Seed / Import (implementiert)

Der deterministische Knowledge-Build, der neutrale Seed und der Snapshot-Import sind implementiert und bauen auf dem #9-Ingestion und den #15-Verträgen auf:

- **Build:** `build_knowledge_snapshot` erzeugt aus `RepositoryIngestionResult`-Eingängen einen stabilen `knowledge-snapshot/v1`-Snapshot mit Manifest, Build-Metadaten und kanonisierter JSON-Serialisierung.
- **Seed-Fixture:** `tests/fixtures/knowledge/knowledge_snapshot.neutral.v1.json` ist der committete, produktneutrale Seed-Snapshot auf Basis des Ingestion-Fixtures unter `tests/fixtures/connectors/` (profilgesteuert, ohne Claire-, Trading- oder Live-Bezug).
- **Import:** `import_knowledge_snapshot` führt einen Snapshot atomar in einen importierenden Ziel-Store ein (Validation-First, keine Teil-Commits; identische Records werden übersprungen, geänderte aktualisiert, fehlende via Tombstone entfernt).
- **Write-Grenze:** KB-Writes sind reproduzierbare Build-Artefakte und nicht mit allgemeinen produktiven Agent-Memory-Writes zu verwechseln; letztere bleiben nicht freigegeben.

## Slice #7 — Hybrid Retrieval / Knowledge Reasoning (implementiert)

Der produktneutrale Retrieval-Layer konsumiert die stabilen #15-Index-/Graph-Verträge und die reproduzierbaren #16-Knowledge-Artefakte. Die öffentliche Surface liegt unter `agent_brain.retrieval`.

- **Candidate Collection:** `collect_candidates` dedupliziert `IndexRecord`-Eingänge und erzeugt stabil sortierte `RetrievalCandidate`-Werte.
- **Hybrid Ranking:** `rank_candidates` kombiniert injizierte lexikalische/Graph-Signale, Source Priority und konservative Deferred-Faktoren deterministisch; jede Wertung erhält eine strukturierte `RankingExplanation`.
- **Graph / Impact:** `compute_graph_signals`, `bounded_graph_traversal` und `annotate_impact` arbeiten in-memory auf `GraphEdge`-Verträgen.
- **Required Reads / Stop:** `resolve_retrieval_required_reads` verwendet den bestehenden `RequiredReadsProfile`-Resolver; `resolve_retrieval_stop` materialisiert `PolicyDecision` fail-conservativ als `RetrievalStop`.
- **E2E:** `run_retrieval` liefert einen deterministischen `RetrievalResult`; neutrale Retrieval-Fixtures sind an die Provenance des #16-Seeds gebunden.

Implementierungsplan: [Hybrid Retrieval und Knowledge Reasoning](superpowers/plans/2026-10-21-hybrid-retrieval-knowledge-reasoning.md).

## Slice #8 — Evidence / Decisions / Trust (implementiert)

- **Paket:** `agent_brain.evidence` — fünfstufige, gerichtete Pipeline Resolution → Decisions → Integrity → Quality → Trust.
- **Contracts:** konsumiert unverändert #15 (`EvidenceRef` / `ClaimRef`) und #37 (`TemporalEnvelope`, `Provenance`, `ResolutionMeta`, `ResolutionState`).
- **Zeit:** `evaluate_freshness`, `detect_scope_drift` und `detect_contradictions` nutzen explizites `as_of`; `ResolutionState` wird read-side abgeleitet.
- **Tests:** `tests/evidence/` mit neutralen Fixtures unter `tests/fixtures/evidence/`.
- **Plan:** [Evidence, Decisions und Trust](superpowers/plans/2026-10-21-evidence-decisions-trust.md).

## P0 #37 — Temporal / Provenance / Supersession (implementiert)

Die bestehenden `EvidenceRef`-/`ClaimRef`-Typen bleiben reine Referenzen. Ergänzend stehen backend-neutrale Contracts für die Semantik bereit, die Evidence- und Memory-Reads gemeinsam benötigen:

- `TemporalEnvelope`: `known_at`, optionale Realwelt-Gültigkeit (`valid_from` / `valid_until`) und optionales `system_as_of` als Storage-/Read-Snapshot-Metadatum.
- `Provenance` + `SourceSpan`: strukturierte Quelle, optionale exakte 0-based/end-exclusive Unicode-Spans und Ableitungs-Linie.
- `ResolutionMeta`: Supersession-Referenzen sowie getrennte `source_trust`-/`confidence`-Werte.
- `ResolutionState`: read-side Enum; `CURRENT / STALE / SUPERSEDED / UNKNOWN` wird abgeleitet und nicht als Wahrheit im Metadata-Contract gespeichert.

## P1 #39 — KnowledgeStore / MemoryStore / MemoryScope (implementiert)

Backend-neutrale, read-only Store-Ports und ein typisierter, fail-closed `MemoryScope` liegen unter `agent_brain.memory`:

- `KnowledgeStore` / `MemoryStore` als Protocols ohne SurrealDB- oder Agent-Memory-SDK-Typen.
- `MemoryScope` verlangt explizite Kind-/Identitätsfelder; fehlender Scope ist niemals still global.
- Fixture-/In-Memory- und Unavailable-Adapter trennen `UNAVAILABLE`, `EMPTY` und `ABSENT`.
- Keine generische Write-/Remember-/Consolidate-Surface.

## Slice #10 / #11 — Memory Read / Recall / Rediscovery (implementiert)

Der fail-closed Memory-Read-Pfad liegt unter `agent_brain.memory.read` und konsumiert unverändert #39 (`MemoryStore` / `MemoryScope`) sowie #37 (`TemporalEnvelope` / `Provenance` / `ResolutionMeta` / `ResolutionState`):

- **Recall:** `MemoryReadService` lädt scoped Records, reichert sie über `MemoryEntryCatalog` an und leitet `CURRENT / STALE / SUPERSEDED / UNKNOWN` ab.
- **Provenance-Gate:** fehlende Evidence-/Lineage-Metadaten → nicht belastbar (`MISSING_METADATA != TRUSTED`).
- **TTL / Freshness:** `ttl_seconds`, `valid_from` / `valid_until` und Supersession; Boundary-Cases getestet.
- **Live-State:** optionale Claims werden gegen injizierte Live-Checker revalidiert; GitHub-/Repo-Live gewinnen immer; unavailable ≠ confirmed.
- **Rediscovery:** `prove_cross_session_rediscovery` belegt scoped Cross-Session-Recall ohne Scope-Leakage.
- **Grenzen:** keine allgemeinen produktiven Memory-Writes, kein zweiter Store-/Scope-/Provenance-Contract.

## Slice #11 — Distribution / Versionierung / Consumer Contract (implementiert)

Externe Consumer können Agent Brain über eine exakte Package-Version (`agent-brain==X.Y.Z`) bzw. den passenden Git-Tag `vX.Y.Z` pinnen, Public-Surface-Kompatibilität prüfen sowie Upgrade/Rollback reproduzierbar ausführen:

- [Distribution README](distribution/README.md)
- [Consumer Contract](distribution/CONSUMER_CONTRACT.md)
- Python-API: `agent_brain.distribution`
- Neutraler Consumer-Smoke: `tests/fixtures/distribution/neutral_consumer/`

## Slice #12 — CLI / Protocol Surface (implementiert)

Agent Brain ist ohne Claire und ohne privaten MCP bedienbar. Die gemeinsame Application Surface liegt unter `agent_brain.protocol`; die CLI ist ein dünner Transport (`agent-brain` / `python -m agent_brain.cli`):

- [Protocol README](protocol/README.md)
- Operationen: `version`, `health`, `capabilities`, `context_read`, `retrieval`, `evidence`, `memory_read`, `surreal_read`
- strukturierte Fehler, Health-/Capability-Readback, read-only Boundary
- optionaler host-neutraler MCP-Adapter ohne SDK-Pflichtabhängigkeit
- Neutraler Protocol-Consumer-Smoke: `tests/fixtures/protocol/neutral_protocol_consumer/`

## #73 — cdb_context Multi-Surface Plugin (abgeschlossen)

Die vier historischen Delivery-Stufen sind vollständig abgenommen:

1. `CDB_CONTEXT_CAPABILITY_FOUNDATION_GO`
2. `LOCAL_HOST_SURFACES_GO`
3. `CHATGPT_AGENT_BRAIN_APP_GO`
4. finale Vier-Host-Acceptance

Der gemeinsame Capability Contract läuft auf ChatGPT, Claude Code, Cursor und OpenCode. Der Release `0.3.4` / `v0.3.4` erzwingt UTF-8 im gemeinsamen stdio-Server; globale Encoding-Workarounds sind keine Voraussetzung.

- [Capability Architecture](capabilities/README.md)
- [cdb_context Contract](capabilities/CDB_CONTEXT_CONTRACT.md)
- [Host Surfaces](hosts/README.md)
- [Goal-4-Evidence](evidence/agent_brain_issue73_goal4.v1.json)

Finaler Exit von #73:

`AGENT_BRAIN_CDB_CONTEXT_MULTI_SURFACE_OPERATIONAL`

## Abgeschlossene SurrealDB- und Memory-Tracks

- **#65 / #89 / #64 — SurrealDB Foundation + durable Improvement-Persistenz:** `SURREALDB_AGENT_BRAIN_FOUNDATION_OPERATIONAL`.
- **#36 — Memory Architecture Hardening:** Temporalität, Provenance, Supersession, Store-/Scope-Boundaries und native Memory-Read-Baseline sind abgeschlossen.
- **#40 — SurrealDB Agent Memory Evaluation:** `REJECT_FOR_NOW`; kein produktiver Agent-Memory-Adapter wurde eingeführt.

Improvement-Writes bleiben eine eigene eng typisierte Domain-Surface. `KnowledgeStore` und `MemoryStore` bleiben read-only; es gibt keine allgemeine `brain.write()`-/`remember()`-/`consolidate()`-API.

## Kernfähigkeiten heute

1. Repositories und ausgewählte Dokumente einlesen und strukturieren.
2. Code, Dokumentation, Entscheidungen und Evidence miteinander verknüpfen.
3. Relevanten Kontext für einen Auftrag gezielt abrufen.
4. Aussagen auf Quellen, Aktualität und Widersprüche prüfen.
5. frühere Entscheidungen nachvollziehbar wiedergeben.
6. begrenztes, quellengestütztes Memory über Sessions hinweg bereitstellen.
7. anderen Systemen strukturierte Briefings und Trust-Zusammenfassungen liefern.
8. das Improvement Blackboard über eine eng typisierte, durable Persistenz betreiben.

Optional nicht erreichbare Backends bleiben explizit `UNAVAILABLE`/degraded und werden nicht als leere oder bestätigte Wahrheit interpretiert.

## Was Agent Brain ausdrücklich nicht sein soll

- keine zweite Source of Truth,
- keine Trading-Runtime,
- keine Live-/Echtgeld-Freigabeinstanz,
- kein unkontrollierter Memory-Speicher,
- kein Sammelbecken für produktspezifische Geschäftslogik,
- keine Voraussetzung für private ChatGPT-Operator-Zugänge.

## Extraction-Roadmap — vollständig abgeschlossen

```text
0  Extraction Canon                 #3   abgeschlossen
1  Repository Scaffold              #4   abgeschlossen
2  Portable Foundation              #5   abgeschlossen
3  Shared Contracts                 #15  abgeschlossen
4  Context / Briefing               #6   abgeschlossen
5  Repo Ingestion                    #9   abgeschlossen
6  Knowledge Build / Seed            #16  abgeschlossen
7  Retrieval                         #7   abgeschlossen
8  Evidence / Trust                  #8   abgeschlossen
9  SurrealDB Read                    #10  abgeschlossen
10 Memory Read                       #11  abgeschlossen
11 Distribution / Versionierung      #17  abgeschlossen
12 CLI / Protocol                    #12  abgeschlossen
13 Claire Cutover                    #13  abgeschlossen
14 Parity / Dual Run                 #18  abgeschlossen
15 Genericity / Cleanup              #19  abgeschlossen
```

Meta-Exit von #2:

`AGENT_BRAIN_EXTRACTION_CONSUMERIZATION_COMPLETE`

Historische Slice-Pläne, Audit-SHAs und Exit-Evidence bleiben bewusst unverändert und dokumentieren den damaligen Delivery-Zustand.

## Ergebnis von Slice 0

Der Extraction Canon hat festgelegt:

- generische Komponenten → `MOVE`,
- generisches Prinzip mit Claire-spezifischer Ausprägung → `ADAPTER`,
- Claire-Produkt-/Operator-Flächen → `STAY`,
- allgemeine produktive Agent-Memory-Write-Flächen → `DEFER`.

Persistierter State wird getrennt behandelt:

- Git-/GitHub-/Ledger-/Upstream-Mirrors → `REBUILD_FROM_SOURCE`,
- SurrealDB-primary Evidence/Claims/Memory → `MIGRATE`, falls tatsächlich vorhanden und valide,
- verbotene/ungültige Daten → `DROP_WITH_REASON`,
- allgemeine produktive neue Memory Writes → `DEFER`.

Details: [State Transition](extraction/STATE_TRANSITION.md).

## Aktueller Arbeitsmodus — 2026-11-01

**Maintenance / Consumer-driven Development.** Die geplanten Extraction-, Multi-Surface-, SurrealDB-Foundation-, durable-Improvement- und Memory-Hardening-Tracks sind abgeschlossen.

Aktuell existiert kein offener Produkt-/Delivery-Track. [#25 Repo Health Book](https://github.com/jannekbuengener/agent-brain/issues/25) bleibt als kontinuierliche Operations-/Evidence-Fläche bewusst offen und ist kein Delivery-Backlog.

Neue Delivery-Arbeit entsteht nur aus konkretem Consumer-Bedarf, einem belegten Scout-/Health-Finding oder einer neuen klar abgegrenzten Capability-Anforderung. GitHub-/Repo-Live-State bleibt für jeden Re-entry maßgeblich.
