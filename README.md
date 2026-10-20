# Agent Brain

**Agent Brain** wird der eigenständige, generische Wissens-, Kontext-, Evidence-, Decision-, Memory- und Retrieval-Kern für Janneks KI-Agenten.

Das Projekt entsteht aus dem heute in **Claire de Binare** eingebauten Context-/Agent-Brain-System. Ziel ist keine Neuentwicklung, sondern eine kontrollierte Extraktion: generische Brain-Funktionen wandern hierher, Claire-spezifische Trading-, Live-Readiness- und Policy-Regeln bleiben in Claire.

## Kurz erklärt

Agent Brain soll Agenten dabei helfen, schnell zu verstehen:

- welches Repository sie gerade bearbeiten,
- welche Entscheidungen bereits getroffen wurden,
- welche Dokumente, Dateien und Issues relevant sind,
- welche Aussagen durch echte Quellen belegt sind,
- welche Informationen alt, widersprüchlich oder unsicher sind,
- und welcher Kontext aus früheren Läufen wiederverwendet werden darf.

**Wichtig:** Agent Brain ist Kontext- und Evidence-Infrastruktur. Es ersetzt niemals das aktuelle Repository oder GitHub als Live-Wahrheit und besitzt keine Live-Trading- oder Ausführungsautorität.

## Start hier

- [Start hier](docs/START_HIER.md)
- [Datenflüsse und Mermaid-Diagramme](docs/DATENFLUESSE.md)
- [Extraction Design: aus Claire de Binare herauslösen](docs/superpowers/specs/2026-10-20-agent-brain-extraction-design.md)
- [Extraction Epic #2](https://github.com/jannekbuengener/agent-brain/issues/2)

## Planung und Slices

Die operative Extraktion wird über **Epic #2** und die verlinkten Child-Slices #3–#13 gesteuert. Das Epic enthält außerdem den aktuellen **Gap Audit** und den Dependency Flow.

- [Epic #2 — Agent Brain aus Claire de Binare extrahieren](https://github.com/jannekbuengener/agent-brain/issues/2)
- [Slice #3 — Extraction Canon](https://github.com/jannekbuengener/agent-brain/issues/3)
- [Slice #4 — Repository-Baseline](https://github.com/jannekbuengener/agent-brain/issues/4)
- [Slice #5 — Portable Foundation](https://github.com/jannekbuengener/agent-brain/issues/5)
- [Slice #6 — Context Package / Briefing](https://github.com/jannekbuengener/agent-brain/issues/6)
- [Slice #7 — Retrieval / Knowledge Reasoning](https://github.com/jannekbuengener/agent-brain/issues/7)
- [Slice #8 — Evidence / Decisions / Trust](https://github.com/jannekbuengener/agent-brain/issues/8)
- [Slice #9 — Repository Ingestion / Connectors](https://github.com/jannekbuengener/agent-brain/issues/9)
- [Slice #10 — SurrealDB Read Runtime](https://github.com/jannekbuengener/agent-brain/issues/10)
- [Slice #11 — Memory Read Side](https://github.com/jannekbuengener/agent-brain/issues/11)
- [Slice #12 — CLI / Protocol Surface](https://github.com/jannekbuengener/agent-brain/issues/12)
- [Slice #13 — Claire Cutover / Parity / Genericity](https://github.com/jannekbuengener/agent-brain/issues/13)

## Dokumentationsprinzip

Die GitHub-Dokumentation wird **Human First** geschrieben:

- Deutsch als Standardsprache für README, Architektur, Runbooks und Issues.
- Zweck und Wirkung vor Implementierungsdetails.
- Technische Begriffe werden beim ersten Auftreten erklärt.
- Datenflüsse und Beziehungen werden bevorzugt mit Mermaid visualisiert.
- Maschinenverträge, APIs, Schemafelder und Code dürfen weiterhin präzise englische Bezeichner verwenden.

## Aktueller Status

**Planungs- und Extraktionsphase mit offenen Architektur-Gaps.** Noch kein produktiver Brain-Code wurde aus Claire de Binare verschoben. Der aktuelle Gap-Stand wird im [Extraction Epic #2](https://github.com/jannekbuengener/agent-brain/issues/2) gepflegt.
