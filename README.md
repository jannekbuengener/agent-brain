# Agent Brain

**Agent Brain** wird der eigenständige, generische Wissens-, Kontext-, Evidence-, Decision-, Memory- und Retrieval-Kern für Janneks KI-Agenten.

Das Projekt entsteht aus dem heute in **Claire de Binare** eingebauten Context-/Agent-Brain-System. Ziel ist keine Neuentwicklung, sondern eine kontrollierte Extraktion: generische Brain-Funktionen wandern hierher, Claire-spezifische Trading-, Live-Readiness- und Policy-Regeln bleiben in Claire.

## Kurz erklärt

Agent Brain soll Agenten dabei helfen, schnell zu verstehen:

- welches Repository sie bearbeiten,
- welche Entscheidungen bereits getroffen wurden,
- welche Dokumente, Dateien und Issues relevant sind,
- welche Aussagen durch echte Quellen belegt sind,
- welche Informationen alt, widersprüchlich oder unsicher sind,
- und welcher Kontext aus früheren Läufen wiederverwendet werden darf.

**Wichtig:** Agent Brain ist Kontext- und Evidence-Infrastruktur. Es ersetzt niemals GitHub oder das aktuelle Repository als Live-Wahrheit und besitzt keine Live-Trading- oder Ausführungsautorität.

## Start hier

- [Start hier](docs/START_HIER.md)
- [Datenflüsse und Mermaid-Diagramme](docs/DATENFLUESSE.md)
- [Extraction Canon — Ergebnis von Slice 0](docs/extraction/README.md)
- [Extraction Design](docs/superpowers/specs/2026-10-20-agent-brain-extraction-design.md)
- [Extraction Epic #2](https://github.com/jannekbuengener/agent-brain/issues/2)

## Roadmap v2

Die operative Extraktion besteht aus **16 Slices (0–15)**:

```text
#3  Slice 0   Extraction Canon
#4  Slice 1   Repository Scaffold
#5  Slice 2   Portable Foundation
#15 Slice 3   Shared Source / Index / Evidence Contracts
#6  Slice 4   Context Package / Briefing
#9  Slice 5   Repository Ingestion / Connectors
#16 Slice 6   Knowledge Build / Seed / Import
#7  Slice 7   Retrieval / Knowledge Reasoning
#8  Slice 8   Evidence / Decisions / Trust
#10 Slice 9   SurrealDB Read Runtime
#11 Slice 10  Memory Read Side
#17 Slice 11  Distribution / Versionierung / Consumer Contract
#12 Slice 12  CLI / Protocol Surface
#13 Slice 13  Claire Adapter / Consumer Cutover
#18 Slice 14  Parity / Dual Run / E2E
#19 Slice 15  Genericity Proof / Claire Cleanup
```

Slice 0 hat die Ownership- und State-Grenzen konkretisiert. Für tatsächlich vorhandenen SurrealDB-primary State existiert zusätzlich [#21 — State Migration Gate](https://github.com/jannekbuengener/agent-brain/issues/21).

## Wichtige Write-Trennung

- **Knowledge-/Index-Build-Writes:** kontrolliert und reproduzierbar in Slice #16 vorgesehen.
- **Produktive Agent-Memory-Writes:** in diesem Epic weiterhin `DEFER`.

Das sind zwei unterschiedliche Sicherheits- und Datenklassen und dürfen nicht vermischt werden.

## Dokumentationsprinzip

Die GitHub-Dokumentation wird **Human First** geschrieben:

- Deutsch als Standardsprache für README, Architektur, Runbooks und Issues.
- Zweck und Wirkung vor Implementierungsdetails.
- Technische Begriffe werden beim ersten Auftreten erklärt.
- Datenflüsse und Beziehungen werden bevorzugt mit Mermaid visualisiert.
- Maschinenverträge, APIs, Schemafelder und Code dürfen weiterhin präzise englische Bezeichner verwenden.

## Aktueller Status

**`SLICE_0_VALIDATED / READY_FOR_SLICE_1`** — die Komponenten-Ownership, State-Transition und Parity-Gates sind auditiert. Noch wurde kein produktiver Brain-Code aus Claire de Binare verschoben. Nächster linearer Slice: [#4 — Repository Scaffold](https://github.com/jannekbuengener/agent-brain/issues/4).