# Start hier — Agent Brain

## Was ist Agent Brain?

Agent Brain ist das gemeinsame Kontext- und Wissenssystem für KI-Agenten. Es entscheidet nicht selbst, **was** ein Produkt tun darf. Es hilft Agenten, den aktuellen Zustand eines Projekts korrekt zu verstehen, relevante Zusammenhänge wiederzufinden und Aussagen mit Evidence zu belegen.

Das System wird aus dem bestehenden Context-/Agent-Brain von Claire de Binare herausgelöst und als eigenständiges Repository generalisiert.

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
8. [Extraction Canon](extraction/README.md) — was aus Claire wohin gehört und wie bestehender State behandelt wird.
9. [Repository Adoption How-to](extraction/REPOSITORY_ADOPTION_HOWTO.md) — wiederverwendbares Verfahren für weitere Repositories: Live-State, Canon-Audit, Ownership, State, Parity, Adoption und Closeout.
10. [Extraction Design](superpowers/specs/2026-10-20-agent-brain-extraction-design.md) — Zielarchitektur und Migrationslogik.
11. [Epic #2](https://github.com/jannekbuengener/agent-brain/issues/2) — operative Roadmap und Issue-Status.

## Slice #9 — Repository Ingestion / Connectors (implementiert)

Der read-only, produktneutrale Ingestionskern ist implementiert. Er liest explizit profilierte lokale Repositories und erzeugt deterministische #15-Ausgaben für den Knowledge-Build #16:

- [Source → Target Matrix](extraction/SLICE_5_SOURCE_TARGET_MATRIX.md) — Claire-Verhalten: übernehmen, generalisieren, Adapter/Stay/Defer.
- [Acceptance / Parity / Risk Matrix](extraction/SLICE_5_ACCEPTANCE_PARITY_MATRIX.md) — jedes AC mit Beweis und Negative Controls.
- [Implementation Plan](superpowers/plans/2026-10-20-repository-ingestion-connectors.md) — TDD-/Task-Reihenfolge.
- [SurrealDB Reference Landscape](external-docs/surrealdb-reference-landscape.md) — Reuse-/Research-Routing; keine aktuelle Runtime-Dependency.

Die Entscheidungen über Claire-vs-Core, DB-Writes, Repo-Identität und SurrealDB-Aktivierung sind damit festgelegt; ein Consumer folgt dem Connectors-README und den #15-Verträgen.

## Slice #6 — Knowledge Build / Seed / Import (implementiert)

Der deterministische Knowledge-Build, der neutrale Seed und der Snapshot-Import sind implementiert und bauen auf dem #9-Ingestion und den #15-Verträgen auf:

- **Build:** `build_knowledge_snapshot` erzeugt aus `RepositoryIngestionResult`-Eingängen einen stabilen `knowledge-snapshot/v1`-Snapshot mit Manifest, Build-Metadaten und kanonisierter JSON-Serialisierung.
- **Seed-Fixture:** `tests/fixtures/knowledge/knowledge_snapshot.neutral.v1.json` ist der committete, produktneutrale Seed-Snapshot auf Basis des Ingestion-Fixtures unter `tests/fixtures/connectors/` (profilgesteuert, ohne Claire-, Trading- oder Live-Bezug).
- **Import:** `import_knowledge_snapshot` führt einen Snapshot atomar in einen importierenden Ziel-Store ein (Validation-First, keine Teil-Commits; identische Records werden übersprungen, geänderte aktualisiert, fehlende via Tombstone entfernt).
- **Write-Grenze:** KB-Writes sind reproduzierbare Build-Artefakte und nicht mit produktiven Agent-Memory-Writes zu verwechseln; letztere bleiben im Epic `DEFER`.

## Slice #7 — Hybrid Retrieval / Knowledge Reasoning (implementiert)

Der produktneutrale Retrieval-Layer konsumiert die stabilen #15-Index-/Graph-Verträge und die reproduzierbaren #16-Knowledge-Artefakte. Die öffentliche Surface liegt unter `agent_brain.retrieval`.

- **Candidate Collection:** `collect_candidates` dedupliziert `IndexRecord`-Eingänge und erzeugt stabil sortierte `RetrievalCandidate`-Werte.
- **Hybrid Ranking:** `rank_candidates` kombiniert injizierte lexikalische/Graph-Signale, Source Priority und konservative Deferred-Faktoren deterministisch; jede Wertung erhält eine strukturierte `RankingExplanation`.
- **Graph / Impact:** `compute_graph_signals`, `bounded_graph_traversal` und `annotate_impact` arbeiten in-memory auf `GraphEdge`-Verträgen. Es gibt keine DB-Annahme und keine Trust-/Decision-Autorität.
- **Required Reads / Stop:** `resolve_retrieval_required_reads` reused den bestehenden `RequiredReadsProfile`-Resolver; `resolve_retrieval_stop` materialisiert `PolicyDecision` fail-conservativ als `RetrievalStop`.
- **E2E:** `run_retrieval` liefert einen deterministischen `RetrievalResult`; neutrale Retrieval-Fixtures sind an die Provenance des #16-Seeds `tests/fixtures/knowledge/knowledge_snapshot.neutral.v1.json` gebunden.
- **Grenzen:** Evidence-/Decision-/Trust-Semantik bleibt Slice #8; eine produktive SurrealDB-Read-Runtime bleibt Slice #10. Semantic/Vector-Signale sind bis dahin konservativ deferred, nicht implizit erfunden.

Implementierungsplan: [Hybrid Retrieval und Knowledge Reasoning](superpowers/plans/2026-10-21-hybrid-retrieval-knowledge-reasoning.md).

## Slice #8 — Evidence / Decisions / Trust (implementiert)

- **Paket:** `agent_brain.evidence` — fünfstufige, gerichtete Pipeline Resolution → Decisions → Integrity → Quality → Trust.
- **Contracts:** konsumiert unverändert #15 (`EvidenceRef` / `ClaimRef`) und #37 (`TemporalEnvelope`, `Provenance`, `ResolutionMeta`, `ResolutionState`); Slice-8-Overlays und Policies liegen in `agent_brain.evidence.contract`.
- **Zeit:** nur Stufe 3 (`evaluate_freshness`, `detect_scope_drift`, `detect_contradictions`) nutzt explizites `as_of`; `ResolutionState` wird ausschließlich in `freshness.py` abgeleitet.
- **Tests:** `tests/evidence/` mit neutralen Fixtures unter `tests/fixtures/evidence/`.
- **Plan:** [Evidence, Decisions und Trust](superpowers/plans/2026-10-21-evidence-decisions-trust.md).

## P0 #37 — Temporal / Provenance / Supersession (implementiert)

Die bestehenden `EvidenceRef`-/`ClaimRef`-Typen bleiben reine Referenzen. Ergänzend stehen nun backend-neutrale Contracts für die Semantik bereit, die #8 und #11 gemeinsam benötigen:

- `TemporalEnvelope`: `known_at`, optionale Realwelt-Gültigkeit (`valid_from` / `valid_until`) und optionales `system_as_of` als Storage-/Read-Snapshot-Metadatum.
- `Provenance` + `SourceSpan`: strukturierte Quelle, optionale exakte 0-based/end-exclusive Unicode-Spans und Ableitungs-Linie.
- `ResolutionMeta`: Supersession-Referenzen sowie getrennte `source_trust`-/`confidence`-Werte.
- `ResolutionState`: read-side Enum; `CURRENT / STALE / SUPERSEDED / UNKNOWN` wird später abgeleitet und nicht als Wahrheit im Metadata-Contract gespeichert.

Die Contracts enthalten keine SurrealDB-/Agent-Memory-Runtime, keine produktiven Writes, kein Last-Write-Wins und keinen Freshness-/Trust-Resolver.

Runtime-/Storage-Inventar für #38: [SurrealDB Runtime Baseline — 2026-10-21](surrealdb/RUNTIME_BASELINE_2026-10-21.md).

## Was Agent Brain später können soll

1. Repositories und ausgewählte Dokumente einlesen und strukturieren.
2. Code, Dokumentation, Entscheidungen und Evidence miteinander verknüpfen.
3. Relevanten Kontext für einen Auftrag gezielt abrufen.
4. Aussagen auf Quellen, Aktualität und Widersprüche prüfen.
5. frühere Entscheidungen nachvollziehbar wiedergeben.
6. begrenztes, quellengestütztes Memory über Sessions hinweg bereitstellen.
7. anderen Systemen strukturierte Briefings und Trust-Zusammenfassungen liefern.

## Was Agent Brain ausdrücklich nicht sein soll

- keine zweite Source of Truth,
- keine Trading-Runtime,
- keine Live-/Echtgeld-Freigabeinstanz,
- kein unkontrollierter Memory-Speicher,
- kein Sammelbecken für produktspezifische Geschäftslogik,
- keine Voraussetzung für private ChatGPT-Operator-Zugänge.

## Roadmap

```text
0  Extraction Canon                 #3   abgeschlossen
1  Repository Scaffold              #4   abgeschlossen
2  Portable Foundation              #5   abgeschlossen
3  Shared Contracts                 #15  abgeschlossen
4  Context / Briefing               #6   abgeschlossen
5  Repo Ingestion                    #9   abgeschlossen
6  Knowledge Build / Seed            #16  abgeschlossen
7  Retrieval                         #7   abgeschlossen
8  Evidence / Trust                  #8   implementiert (Slice 8 Pipeline)
9  SurrealDB Read                    #10
10 Memory Read                       #11
11 Distribution / Versionierung      #17
12 CLI / Protocol                    #12
13 Claire Cutover                    #13
14 Parity / Dual Run                 #18
15 Genericity / Cleanup              #19
```

Zusätzlich existiert [#21 — State Migration Gate](https://github.com/jannekbuengener/agent-brain/issues/21). Dieses Gate übernimmt **keine** allgemeinen Knowledge-Mirrors, sondern schützt nur echten SurrealDB-primary State vor stillem Verlust und blockiert die linearen Foundation-/Contract-/Context-Slices nicht.

## Ergebnis von Slice 0

Der Extraction Canon hat festgelegt:

- generische Komponenten → `MOVE`,
- generisches Prinzip mit Claire-spezifischer Ausprägung → `ADAPTER`,
- Claire-Produkt-/Operator-Flächen → `STAY`,
- produktive Agent-Memory-Write-Flächen → `DEFER`.

Persistierter State wird getrennt behandelt:

- Git-/GitHub-/Ledger-/Upstream-Mirrors → `REBUILD_FROM_SOURCE`,
- SurrealDB-primary Evidence/Claims/Memory → `MIGRATE`, falls tatsächlich vorhanden und valide,
- verbotene/ungültige Daten → `DROP_WITH_REASON`,
- produktive neue Memory Writes → `DEFER`.

Details: [State Transition](extraction/STATE_TRANSITION.md).

## Aktueller Arbeitsmodus

**`SLICE_7_DONE / #37_TEMPORAL_PROVENANCE_IMPLEMENTED`**. #37 ist die gemeinsame Contract-Basis vor #8/#11. Nach #37 können #8 und #39 parallel arbeiten; #38 darf parallel ausschließlich read-only die reale SurrealDB-Runtime/Storage-Baseline erfassen. #10 konsumiert später #8 + #39 sowie die Evidence aus #38.
