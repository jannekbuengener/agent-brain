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

## Dokumentationsprinzip

Die GitHub-Dokumentation wird **Human First** geschrieben:

- Deutsch als Standardsprache für README, Architektur, Runbooks und Issues.
- Zweck und Wirkung vor Implementierungsdetails.
- Technische Begriffe werden beim ersten Auftreten erklärt.
- Datenflüsse und Beziehungen werden bevorzugt mit Mermaid visualisiert.
- Maschinenverträge, APIs, Schemafelder und Code dürfen weiterhin präzise englische Bezeichner verwenden.

## Aktueller Status

**Planungs- und Extraktionsphase.** Noch kein produktiver Brain-Code wurde aus Claire de Binare verschoben.
