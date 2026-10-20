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
4. [Entwicklungsbaseline](DEVELOPMENT.md) — Installation, Tests und die aktuell erlaubten Modulgrenzen.
5. [Externe Referenzdokumentation](external-docs/index.md) — `ACTIVE` markiert heute im Repo belegte Technologien; `NEXT`/`REFERENCE`/`PARKED` trennt geplante oder optionale Referenzen davon.
6. [Datenflüsse](DATENFLUESSE.md) — visuelle Mermaid-Erklärung des Systems.
7. [Extraction Canon](extraction/README.md) — was aus Claire wohin gehört und wie bestehender State behandelt wird.
8. [Repository Adoption How-to](extraction/REPOSITORY_ADOPTION_HOWTO.md) — wiederverwendbares Verfahren für weitere Repositories: Live-State, Canon-Audit, Ownership, State, Parity, Adoption und Closeout.
9. [Extraction Design](superpowers/specs/2026-10-20-agent-brain-extraction-design.md) — Zielarchitektur und Migrationslogik.
10. [Epic #2](https://github.com/jannekbuengener/agent-brain/issues/2) — operative Roadmap und Issue-Status.

## Slice #9 vor Implementierung

Für Repository Ingestion / Connectors sind die Entscheidungen vor Codebeginn jetzt getrennt dokumentiert:

- [Source → Target Matrix](extraction/SLICE_5_SOURCE_TARGET_MATRIX.md) — Claire-Verhalten: übernehmen, generalisieren, Adapter/Stay/Defer.
- [Acceptance / Parity / Risk Matrix](extraction/SLICE_5_ACCEPTANCE_PARITY_MATRIX.md) — jedes AC mit späterem Beweis und Negative Controls.
- [Implementation Plan](superpowers/plans/2026-10-20-repository-ingestion-connectors.md) — TDD-/Task-Reihenfolge.
- [SurrealDB Reference Landscape](external-docs/surrealdb-reference-landscape.md) — Reuse-/Research-Routing; keine aktuelle Runtime-Dependency.

Damit muss ein Implementierungsagent keine Architekturentscheidung über Claire-vs-Core, DB-Writes, Repo-Identität oder SurrealDB-Aktivierung neu erfinden.

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
4  Context / Briefing               #6   abgeschlossen / aktuelle Code-Baseline
5  Repo Ingestion                    #9   READY_FOR_IMPLEMENTATION
6  Knowledge Build / Seed            #16
7  Retrieval                         #7
8  Evidence / Trust                  #8
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

**`SLICE_5_REPOSITORY_INGESTION — READY_FOR_IMPLEMENTATION`**. Produktcode für #9 ist noch nicht implementiert. Scope, Source→Target-Grenzen, Acceptance/Parity/Negative Controls, Reuse-Routing und Implementierungsplan sind vorab festgelegt. Die nächste erlaubte Phase ist test-first Implementierung von [#9](https://github.com/jannekbuengener/agent-brain/issues/9); nach erfolgreichem Merge folgt #16.
