# Agent Brain

**Agent Brain** ist der eigenständige, generische Wissens-, Kontext-, Evidence-, Decision-, Memory- und Retrieval-Kern für Janneks KI-Agenten.

Das Projekt wurde kontrolliert aus dem Context-/Agent-Brain von **Claire de Binare** extrahiert und generalisiert. Generische Brain-Funktionen leben hier; Claire-spezifische Trading-, Live-Readiness- und Policy-Regeln bleiben in Claire.

## Kurz erklärt

Agent Brain hilft Agenten dabei, schnell zu verstehen:

- welches Repository sie bearbeiten,
- welche Entscheidungen bereits getroffen wurden,
- welche Dokumente, Dateien und Issues relevant sind,
- welche Aussagen durch echte Quellen belegt sind,
- welche Informationen alt, widersprüchlich oder unsicher sind,
- und welcher Kontext aus früheren Läufen wiederverwendet werden darf.

**Wichtig:** Agent Brain ist Kontext- und Evidence-Infrastruktur. Es ersetzt niemals GitHub oder das aktuelle Repository als Live-Wahrheit und besitzt keine Live-Trading- oder Ausführungsautorität.

## Start hier

- [Start hier](docs/START_HIER.md)
- [Portable Foundation](docs/foundation/README.md)
- [Gemeinsame Source-/Index-/Evidence-Contracts](docs/contracts/README.md)
- [Context Package und Briefing Core](docs/context/README.md)
- [Repository Ingestion und Connectors](docs/connectors/README.md)
- [Externe technische Referenzen](docs/external-docs/index.md)
- [Distribution / Consumer Contract](docs/distribution/README.md)
- [CLI / Protocol Surface](docs/protocol/README.md)
- [Capability / cdb_context Plugin Surface](docs/capabilities/README.md)
- [Host Surfaces (Claude / Cursor / OpenCode / ChatGPT)](docs/hosts/README.md)
- [Entwicklungsbaseline](docs/DEVELOPMENT.md)
- [Datenflüsse und Mermaid-Diagramme](docs/DATENFLUESSE.md)
- [Extraction Canon — Ergebnis von Slice 0](docs/extraction/README.md)
- [Extraction Design](docs/superpowers/specs/2026-10-20-agent-brain-extraction-design.md)
- [Extraction Epic #2](https://github.com/jannekbuengener/agent-brain/issues/2)

## Repository-, Foundation-, Contract- und Context-Baseline

Das Repository nutzt eine bewusst schmale Python-Basis:

```text
src/agent_brain/
├─ core/        # Portable Foundation
├─ contracts/   # Source / Index / Evidence Contracts
├─ context/     # Context Package / Required Reads / Explanation / Validation / Briefing
├─ retrieval/   # Hybrid Retrieval / Knowledge Reasoning (#7)
├─ memory/      # Memory Read / Store Ports
├─ surrealdb/   # SurrealDB Read Runtime und persistente Adapter
├─ distribution/# Consumer Version / Pin Contract (#17)
├─ protocol/    # Public Application / Protocol Surface (#12)
├─ capabilities/# Host-neutral Capability Layer + cdb_context
├─ cli/         # Standalone CLI Transport (#12)
└─ connectors/  # read-only Repository Ingestion (Slice #9)
```

Die Portable Foundation stellt generische Zeit-, Hashing-, Identitäts-, Provenance-, Source-Priority-, Policy-Hook- und Redaction-Primitiven bereit. Die gemeinsame Contract-Schicht definiert versionierte Repository-/Artifact-, Index-/Graph-, Evidence-/Claim- sowie ergänzende Temporal-/Provenance-/Resolution-Metadaten-Typen. Die Context-Schicht baut darauf deterministische Packages, Required Reads, Self-Explanations, Validation Plans und Briefings auf. Die Connector-Schicht liest produktneutral profilierte lokale Repositories read-only und erzeugt deterministische Ausgaben für den Knowledge-Build.

- Python: `>=3.12`
- Packaging: `pyproject.toml` + `src`-Layout
- Package-Version: `0.3.4`
- Pflicht-Runtime-Abhängigkeiten: keine
- Qualität: Ruff + pytest
- CI: Python 3.12, 3.13 und 3.14

Schnellstart und Testkonventionen: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Historische Extraction-Roadmap — abgeschlossen

Die kontrollierte Extraktion bestand aus **16 Slices (0–15)**. Alle Slices sind abgeschlossen; der Meta-Exit von #2 lautet `AGENT_BRAIN_EXTRACTION_CONSUMERIZATION_COMPLETE`.

```text
#3  Slice 0   Extraction Canon                          abgeschlossen
#4  Slice 1   Repository Scaffold                       abgeschlossen
#5  Slice 2   Portable Foundation                       abgeschlossen
#15 Slice 3   Shared Source / Index / Evidence Contracts abgeschlossen
#6  Slice 4   Context Package / Briefing                 abgeschlossen
#9  Slice 5   Repository Ingestion / Connectors          abgeschlossen
#16 Slice 6   Knowledge Build / Seed / Import            abgeschlossen
#7  Slice 7   Retrieval / Knowledge Reasoning            abgeschlossen
#8  Slice 8   Evidence / Decisions / Trust               abgeschlossen
#10 Slice 9   SurrealDB Read Runtime                      abgeschlossen
#11 Slice 10  Memory Read Side                            abgeschlossen
#17 Slice 11  Distribution / Versionierung                abgeschlossen
#12 Slice 12  CLI / Protocol Surface                      abgeschlossen
#13 Slice 13  Claire Adapter / Consumer Cutover           abgeschlossen
#18 Slice 14  Parity / Dual Run / E2E                     abgeschlossen
#19 Slice 15  Genericity Proof / Claire Cleanup           abgeschlossen
```

Der State-Handoff aus #21 ist ebenfalls abgeschlossen. Historische Slice-/Audit-Dokumente bleiben als Evidence erhalten und werden nicht nachträglich in Gegenwartsdokumentation umgeschrieben.

## Abgeschlossene Cross-Cutting Tracks

- **Multi-Surface Plugin #73:** ChatGPT, Claude Code, Cursor und OpenCode verwenden denselben `cdb_context`-Capability-Contract. Exit: `AGENT_BRAIN_CDB_CONTEXT_MULTI_SURFACE_OPERATIONAL`.
- **SurrealDB Foundation #65 / #89 / #64:** sichere Runtime-/Persistenzbasis, durable Improvement-Persistenz sowie Backup-/Restore- und Parallel-Writer-Evidence sind abgeschlossen. Exit: `SURREALDB_AGENT_BRAIN_FOUNDATION_OPERATIONAL`.
- **Memory Architecture Hardening #36:** Temporalität, Provenance, Supersession, Scope-/Store-Boundaries und native Memory-Read-Baseline sind abgeschlossen.
- **Agent-Memory-Evaluation #40:** Entscheidung `REJECT_FOR_NOW`. Die native Baseline bleibt maßgeblich; es wurde kein produktiver SurrealDB-Agent-Memory-Adapter eingeführt.

## Wichtige Write-Trennung

- **Knowledge-/Index-Build-Writes:** kontrolliert und reproduzierbar über die bestehende Build-/Import-Fläche.
- **Improvement-Writes:** eng typisiert über die Improvement-Domain; durable SurrealDB-Persistenz ist hinter dieser Boundary operational.
- **Allgemeine produktive Agent-Memory-Writes:** weiterhin nicht freigegeben; keine generische `remember()`-/`write()`-/`consolidate()`-Surface.

Diese Daten- und Authority-Klassen dürfen nicht vermischt werden.

## Dokumentationsprinzip

Die GitHub-Dokumentation wird **Human First** geschrieben:

- Deutsch als Standardsprache für README, Architektur, Runbooks und Issues.
- Zweck und Wirkung vor Implementierungsdetails.
- Technische Begriffe werden beim ersten Auftreten erklärt.
- Datenflüsse und Beziehungen werden bevorzugt mit Mermaid visualisiert.
- Maschinenverträge, APIs, Schemafelder und Code dürfen weiterhin präzise englische Bezeichner verwenden.

Der externe Referenzindex trennt aktuell belegte Kern-/Sekundärreferenzen (`P0`/`P1`, jeweils mit Repo-Evidence) von geparkten `P2`-Referenzen. `P2` ist keine Aussage über vorhandene Runtime-Fähigkeiten oder Dependencies. Externe Dokumentation ersetzt nie GitHub-/Repo-Live-State.

## Aktueller Status — 2026-11-01

**Delivery-seitig ist Agent Brain aktuell abgeschlossen.** Extraction/Consumerization, Multi-Surface-Plugin, SurrealDB-Foundation, durable Improvement-Persistenz und Memory-Architecture-Hardening sind live abgenommen und geschlossen.

Das Repository arbeitet damit im Modus **Maintenance / Consumer-driven Development**:

- neue Produkt-/Delivery-Arbeit entsteht aus konkretem Consumer-Bedarf, einem belegten Scout-/Health-Finding oder einer neuen klaren Capability-Anforderung;
- es wird kein Backlog erzeugt, nur um das Repository künstlich „aktiv“ zu halten;
- [#25 Repo Health Book](https://github.com/jannekbuengener/agent-brain/issues/25) bleibt als kontinuierliche Operations-/Evidence-Fläche bewusst offen und ist kein Delivery-Backlog.

GitHub-/Repo-Live-State bleibt für jeden späteren Re-entry maßgeblich.
