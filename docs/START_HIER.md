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

1. [Datenflüsse](DATENFLUESSE.md) — visuelle Mermaid-Erklärung des Systems.
2. [Extraction Canon](extraction/README.md) — was aus Claire wohin gehört und wie bestehender State behandelt wird.
3. [Extraction Design](superpowers/specs/2026-10-20-agent-brain-extraction-design.md) — Zielarchitektur und Migrationslogik.
4. [Epic #2](https://github.com/jannekbuengener/agent-brain/issues/2) — operative Roadmap und Issue-Status.

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
0  Extraction Canon                 #3   abgeschlossen nach Merge des Slice-0-PR
1  Repository Scaffold              #4
2  Portable Foundation              #5
3  Shared Contracts                 #15
4  Context / Briefing               #6
5  Repo Ingestion                    #9
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

Zusätzlich existiert [#21 — State Migration Gate](https://github.com/jannekbuengener/agent-brain/issues/21). Dieses Gate übernimmt **keine** allgemeinen Knowledge-Mirrors, sondern schützt nur echten SurrealDB-primary State vor stillem Verlust.

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

**`SLICE_0_VALIDATED / READY_FOR_SLICE_1`**. Noch keine Brain-Runtime wurde aus Claire verschoben. Nächster linearer Arbeitsscope ist [#4 — Agent-Brain Scaffold und Repository-Baseline](https://github.com/jannekbuengener/agent-brain/issues/4).