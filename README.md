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
- [Portable Foundation](docs/foundation/README.md)
- [Gemeinsame Source-/Index-/Evidence-Contracts](docs/contracts/README.md)
- [Context Package und Briefing Core](docs/context/README.md)
- [Repository Ingestion und Connectors](docs/connectors/README.md)
- [Externe technische Referenzen](docs/external-docs/index.md)
- [Distribution / Consumer Contract](docs/distribution/README.md)
- [CLI / Protocol Surface](docs/protocol/README.md)
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
├─ surrealdb/   # SurrealDB Read Runtime
├─ distribution/# Consumer Version / Pin Contract (#17)
├─ protocol/    # Public Application / Protocol Surface (#12)
├─ cli/         # Standalone CLI Transport (#12)
└─ connectors/  # read-only Repository Ingestion (Slice #9)
```

Die Portable Foundation stellt generische Zeit-, Hashing-, Identitäts-, Provenance-, Source-Priority-, Policy-Hook- und Redaction-Primitiven bereit. Die gemeinsame Contract-Schicht definiert versionierte Repository-/Artifact-, Index-/Graph-, Evidence-/Claim- sowie ergänzende Temporal-/Provenance-/Resolution-Metadaten-Typen. Die Context-Schicht baut darauf deterministische Packages, Required Reads, Self-Explanations, Validation Plans und Briefings auf. Die Connector-Schicht liest produktneutral profilierte lokale Repositories read-only und erzeugt die deterministischen #15-Ausgaben für den späteren Knowledge-Build.

- Python: `>=3.12`
- Packaging: `pyproject.toml` + `src`-Layout
- Runtime-Abhängigkeiten: keine
- Qualität: Ruff + pytest
- CI: Python 3.12, 3.13 und 3.14

Schnellstart und Testkonventionen: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

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

Der Architecture-Hardening-Track [#36](https://github.com/jannekbuengener/agent-brain/issues/36) ergänzt die lineare Roadmap: #37 kanonisiert Temporal-/Provenance-/Supersession-Semantik; #38 inventarisiert die reale SurrealDB-Runtime read-only; #39 definiert die Store-/Scope-Boundary; #40 bleibt ein später, nicht blockierender Agent-Memory-Benchmark.

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

Der externe Referenzindex trennt aktuell belegte Kern-/Sekundärreferenzen (`P0`/`P1`, jeweils mit Repo-Evidence) von geparkten `P2`-Referenzen. `P2` ist keine Aussage über vorhandene Runtime-Fähigkeiten oder Dependencies. Externe Dokumentation ersetzt nie GitHub-/Repo-Live-State.

## Aktueller Status

**`SLICE_7_DONE / #37_TEMPORAL_PROVENANCE_IMPLEMENTED`** — Knowledge Build (#16) und Hybrid Retrieval (#7) sind abgeschlossen. #37 ergänzt jetzt die backend-neutralen Temporal-/Provenance-/Supersession-Contracts. Danach können #8 (Evidence/Trust) und #39 (Store/Scope-Boundary) unabhängig auf dieser Semantik aufbauen; #38 bleibt die parallele read-only Runtime-Baseline.
