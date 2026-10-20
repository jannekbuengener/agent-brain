# SurrealDB Reference Landscape — Agent-Brain Routing

**Status:** `REFERENCE` für #9; `NEXT` für #10/#16/#21  
**Zweck:** Reuse-/Research-Orientierung, **keine** Runtime-Abhängigkeit und **keine** Source of Truth für Agent-Brain-State.

## Warum diese Datei existiert

Im Operator-Umfeld existiert eine breite lokale SurrealDB-Referenzlandschaft mit offiziellen Upstream-Repositories, SDKs, Schema-/Migrationstooling, Agent-/Memory-Komponenten, Beispielen und Community-Referenzen.

Agenten sollen diese Landschaft vor neuem Eigenbau als **Research- und Reference-System** nutzen. Daraus folgt ausdrücklich **nicht**, dass:

- ein lokal vorhandenes Repository aktuell unterstützt wird,
- sein lokaler Ordnername Ownership beweist,
- es automatisch Agent-Brain-Dependency ist,
- eine ältere lokale README aktueller ist als der Upstream,
- ein vorhandener SurrealDB-/Agent-Memory-Baustein automatisch in den aktuellen Slice gehört.

## Wahrheit und Supportstatus

Für SurrealDB-bezogene Architekturfragen gilt:

1. Agent-Brain GitHub/Repo Live für den **aktuellen Agent-Brain-Scope**,
2. aktueller offizieller Upstream / offizielle SurrealDB-Dokumentation für **SurrealDB-Semantik und Supportstatus**,
3. lokale Upstream-Checkouts als schnelle Implementierungs-/Research-Referenz,
4. ältere lokale Ecosystem-Maps nur als historische Orientierung.

**Lokale Existenz ist Evidence für Verfügbarkeit als Research-Material, nicht für aktuellen Support oder Produktaktivierung.**

## Kanonische öffentliche Referenzen

| Thema | Referenz | Agent-Brain-Relevanz |
| --- | --- | --- |
| Dokumentations-Start | https://surrealdb.com/docs | Einstieg für alle SurrealDB-Slices |
| Architektur / Compute & Storage | https://surrealdb.com/docs/learn/data-models/architecture | wichtig für #10/#16; Query-/Storage-Schichten nicht vermischen |
| Deployment | https://surrealdb.com/docs/running/overview | nur falls später eigener Runtime-/Deploy-Scope entsteht |
| SDKs | https://surrealdb.com/docs/languages | #10 bei Auswahl eines Read Adapters |
| AI Agents | https://surrealdb.com/docs/build/ai-agents | Research für Agent-/Protocol-Integrationen, keine automatische Dependency |
| Agent Skills | https://surrealdb.com/docs/build/ai-agents/agent-skills | Reuse-/Agentenwissen, nicht Core-Contract |
| Agent Memory | https://surrealdb.com/docs/agent-memory | Referenz für späteren Memory-Scope; nicht mit lokalem Demo-Repo gleichsetzen |
| Agent-Memory-Integrationen | https://surrealdb.com/docs/agent-memory/integrations | spätere Adapter-/Consumer-Research |
| Schema/Migration | https://surrealdb.com/docs/manage/schema-migration | #16/#21 Research |
| CLI | https://surrealdb.com/docs/reference/cli/surrealdb-cli/overview | Operator-/späterer CLI-Scope |
| REST API | https://surrealdb.com/docs/reference/rest-api | nur wenn #10 einen HTTP-Read-Adapter explizit wählt |
| GitHub-Organisation | https://github.com/surrealdb | aktueller Upstream-/Archivierungsstatus |
| offizielle Docs-Quelle | https://github.com/surrealdb/docs.surrealdb.com | Docs-Implementierung und Quellen |
| Beispiele | https://github.com/surrealdb/examples | Reuse vor Eigenbau |
| Tool-/Community-Index | https://github.com/surrealdb/awesome-surreal | Discovery; Einträge einzeln verifizieren |

## Lokal besonders nützliche Referenzklassen

Die lokale Landschaft enthält bzw. kann enthalten:

| Klasse | Beispiele | Nutzung |
| --- | --- | --- |
| Database Core | `surrealdb` | Query-/DB-Semantik verstehen; nicht in Agent Brain kopieren |
| Python SDK | `surrealdb.py` | #10 Read-Adapter-Research |
| JS/Go SDKs | `surrealdb.js`, `surrealdb.go` | Cross-SDK-Verhalten / Protokollreferenz |
| Schema / Migration | `surrealkit`, `surreal-sync`, `setup-surreal` | #16/#21 Migrations-/Build-Muster prüfen |
| Docs / Examples | `docs.surrealdb.com`, `examples`, `awesome-surreal` | bevorzugte erste Research-Schicht |
| Agent / AI | `agent-skills`, `langchain-surrealdb`, `kaig`, `surrealfs` | spätere Agent-/Memory-/Retrieval-Research |
| Agent Memory Demo | `agent-memory` | Demo-/Research-Code; **nicht** mit dem heutigen Agent-Memory-Produktcode gleichsetzen |
| Storage | `indxdb`; remote ggf. SurrealKV/SurrealMX | Architektur verstehen; Storage nicht als Query-Core behandeln |
| Deployment | `helm-charts`, Docker-/Install-/Download-Repos | geparkt, solange Agent Brain keinen Deploy-Scope hat |

## Legacy-/Status-Fallen

Beim Lesen lokaler Repositories muss der aktuelle Upstream-Status geprüft werden. Bekannte Beispiele aus dem Research-Stand Oktober 2026:

- `surrealmcp` ist Legacy/archiviert; moderne MCP-Optionen über aktuelle offizielle Docs prüfen.
- `fibre` ist archiviert und darf nicht als aktive Foundation angenommen werden.
- `surrealist` ist Legacy; der aktuelle UI-Einstieg ist SurrealDB Studio.
- der lokale `agent-memory`-Checkout ist Demo-/Talk-/Research-Code und nicht automatisch die vollständige Agent-Memory-Produktcodebase.

Diese Beispiele sind bewusst Warnmuster: **vor Reuse immer aktuellen Upstream lesen.**

## Routing nach Agent-Brain-Slice

### #9 — Repository Ingestion / Connectors

Status: **REFERENCE only**.

Erlaubt:

- Repository-/SDK-/Tooling-Muster lesen,
- Ownership-/Origin-Trennung als Designinput verwenden,
- vorhandene Implementierungen vor Eigenbau prüfen.

Nicht erlaubt:

- SurrealDB als Dependency hinzufügen,
- DB-Verbindung aufbauen,
- lokale SurrealDB-Repos als canonical Agent-Brain-Roots behandeln,
- Agent Memory aktivieren.

### #16 — Knowledge Build / Seed / Import

Status: **NEXT / Research**.

Vor Implementierung prüfen:

- aktuelles SurrealDB Schema-/Migrationsmodell,
- SurrealKit als Referenz für Schema Lifecycle, Seed und kontrollierte Rollouts,
- bestehende Agent-Brain-State-Transition-/Migration-Gates.

Auch hier gilt: Reuse-Muster ist nicht automatisch Dependency-Entscheidung.

### #10 — SurrealDB Read Runtime

Status: **NEXT**.

Vor Adapterwahl prüfen:

- aktuelle Python-SDK-/REST-/Embedded-Optionen,
- offizielle Architektur- und Security-Dokumentation,
- lokale SDK-/Example-Repos,
- Agent-Brain Read-only Contract und negative controls.

#10 darf erst dann eine konkrete Bibliothek aktivieren, wenn Repo-Manifest, Tests und Issue-Scope diese Entscheidung explizit tragen.

### #21 — State Migration Gate

Status: **NEXT**.

Schema-/Migrationstooling ist Referenz. Das Gate entscheidet aber anhand des tatsächlich vorhandenen Agent-Brain/Claire-State und nicht anhand dessen, was SurrealDB theoretisch migrieren könnte.

### Memory-Slices

SurrealDB Agent Memory ist eine wichtige externe Referenz. Agent Brain übernimmt daraus **keine produktive Write-Autorität**. Der aktuelle Extraction-Epic hält produktive Agent-Memory-Writes weiterhin `DEFER`.

## Agenten-Workflow: Reuse vor Eigenbau

Bei einer SurrealDB-nahen Aufgabe:

1. aktuelles Agent-Brain-Issue und Repo-Live-State lesen,
2. Status in `docs/external-docs/index.md` prüfen,
3. relevante offizielle SurrealDB-Dokumentation öffnen,
4. falls verfügbar passenden lokalen Upstream-Checkout und dessen README/Tests untersuchen,
5. lokalen Checkout-Origin und aktuellen Upstream-Status verifizieren,
6. entscheiden: **reuse pattern / library dependency / adapter / reference only / reject**,
7. Entscheidung im Slice-Plan dokumentieren,
8. keine Technologie allein wegen lokaler Verfügbarkeit aktivieren.

## Identitätsregel für Repository-Inventare

Für lokale Research-Landschaften müssen mindestens drei Ebenen getrennt bleiben:

```text
local_path
    != configured_repository_identity
    != observed_origin_or_upstream
```

Sie dürfen übereinstimmen, sind aber **nicht dasselbe Feld**. Ein abweichender Origin ist Evidence/Limitation und kein Grund, die konfigurierte Source still umzuschreiben.

Diese Regel ist direkt für Slice #9 verbindlich und später auch für andere Repository-Connectoren wiederzuverwenden.
