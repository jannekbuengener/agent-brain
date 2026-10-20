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

## Wo sehe ich die Datenflüsse?

In [DATENFLUESSE.md](DATENFLUESSE.md). Dort stehen die wichtigsten Mermaid-Diagramme für:

- Gesamtarchitektur,
- Auftrag → Ergebnis,
- Wahrheitshierarchie,
- Knowledge Build versus Memory,
- Extraction Roadmap v2,
- Claire-Cutover und Parity.

## Wo sehe ich die operative Planung?

Die aktuelle Roadmap lebt in [Epic #2](https://github.com/jannekbuengener/agent-brain/issues/2).

Die neue Reihenfolge lautet:

```text
0 Canon
1 Scaffold
2 Portable Foundation
3 Shared Contracts
4 Context / Briefing
5 Repo Ingestion
6 Knowledge Build / Seed
7 Retrieval
8 Evidence / Trust
9 SurrealDB Read
10 Memory Read
11 Distribution / Versionierung
12 CLI / Protocol
13 Claire Cutover
14 Parity / Dual Run
15 Genericity / Cleanup
```

Die vollständigen Issues sind #3–#13 sowie #15–#19. PR #14 war ausschließlich die vorherige Dokumentations-/Gap-Verlinkung und ist kein Slice.

## Warum wurde die Roadmap erweitert?

Beim Gap Audit wurden fünf echte Übergabelücken gefunden:

- Retrieval brauchte stabile Source-/Index-Contracts.
- Der read-only DB-Pfad hatte keinen expliziten Build-/Seed-Pfad.
- Claire hatte noch keinen Versionierungs-/Consumer-Vertrag.
- Der alte Cutover-Slice war zu groß.
- Context Package und Evidence Resolver brauchten einen gemeinsamen Referenzcontract.

Diese Punkte sind jetzt jeweils eigenen Slices oder klaren Slice-Grenzen zugeordnet.

## Noch offenes Gate

Slice #3 / Slice 0 muss bestehenden persistierten Claire-State klassifizieren:

- `REBUILD_FROM_SOURCE`
- `MIGRATE`
- `DROP_WITH_REASON`
- `DEFER`

Erst danach wissen wir, ob zusätzlich ein eigener Legacy-State-Migrationsslice nötig ist.

## Aktueller Arbeitsmodus

**`ROADMAP_V2_READY_FOR_SLICE_0`**. Die Roadmap ist neu geschnitten; der nächste Schritt ist der Extraction Canon. Noch keine Brain-Runtime wird verschoben.