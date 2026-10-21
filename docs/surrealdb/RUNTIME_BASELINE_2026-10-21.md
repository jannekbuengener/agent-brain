# SurrealDB Runtime Baseline — 2026-10-21

**Issue:** #38
**Status:** `BASELINE_CAPTURED / DB_RUNTIME_UNAVAILABLE`

## Zweck

Diese Baseline hält den tatsächlich beobachtbaren SurrealDB-Zustand für Agent Brain fest, ohne einen Server zu starten, den Datastore zu öffnen, Migrationen auszulösen oder Credentials zu materialisieren.

Sie trennt strikt zwischen:

- **Runtime-Evidence** — aktuell laufender Prozess/Endpoint/DB-Read,
- **Deployment-Config-Evidence** — kanonische Claire-Compose-/Query-Konfiguration,
- **Launcher-Evidence** — lokal installierte CLI-Binaries.

Config-Evidence ist **kein** Ersatz für einen DB-backed Read.

## Guardrails des Inventars

- kein SurrealDB-Server gestartet
- Docker Desktop / Docker Daemon nicht gestartet
- kein Container gestartet oder erstellt
- keine DB geöffnet
- keine `INFO`-/`SELECT`-/`VERSION`-Query gegen einen Datastore ausgeführt, weil kein Endpoint erreichbar war
- keine Export-/Import-/Migration ausgeführt
- vorhandene Secret-Datei nur auf Existenz geprüft; Inhalte wurden nicht gelesen

Der Stopp ist absichtlich konservativ: Die kanonische Compose-Datei nutzt ein bewegliches `surrealdb/surrealdb:latest`. Bei unbekanntem vorhandenen Datastore wäre ein Start kein read-only Inventar und könnte versionsabhängige Datastore-Migrationen auslösen.

## Beobachtete Baseline

| Bereich | Evidence | Klassifikation |
|---|---|---|
| laufender SurrealDB-Prozess | kein `surreal*`-Prozess vorgefunden | `OFFLINE` |
| Windows-Service | kein SurrealDB-Service vorgefunden | `ABSENT` |
| Docker Runtime | keine Docker-/dockerd-/com.docker-Prozesse | `OFFLINE` |
| konfigurierter Container | Claire Compose: `cdb_surrealdb` | `CONFIGURED_ONLY` |
| konfiguriertes Image | `surrealdb/surrealdb:latest` | `CONFIGURED_ONLY / VERSION_NOT_PINNED` |
| konfigurierter Storage Path | `surrealkv:/data/surrealdb` | `CONFIGURED_ONLY` |
| Dev Endpoint | `http://127.0.0.1:8010` | `CONFIGURED_ONLY` |
| `/health` | nicht erreichbar | `UNAVAILABLE` |
| `/ready` | nicht erreichbar | `UNAVAILABLE` |
| tatsächliche Server-Version | kein laufender Endpoint / kein DB-backed Read | `UNAVAILABLE` |
| lokaler primärer CLI-Aufruf | `C:\Users\janne\AppData\Local\SurrealDB\surreal.exe` → `2.6.0 for windows on x86_64` | `VERIFIED` |
| zweite lokale Installation | Scoop `current` ist Junction auf `...\surrealdb\3.3.4` | `FILESYSTEM_EVIDENCE_ONLY` |
| Scoop-Binary-Ausführung | `version` lieferte in diesem Inventar keinen Abschluss; Probe wurde beendet | `UNVERIFIED_EXECUTABLE` |
| Secrets-Datei | `%USERPROFILE%\Documents\.secrets\.cdb\SURREALDB_ENV` existiert | `PRESENT / VALUES_NOT_READ` |

### Wichtiger Launcher-Fund

Auf dem Rechner existieren mindestens zwei SurrealDB-Installationspfade. Der zuerst aufgelöste CLI-Pfad ist die verifizierte **2.6.0**-Installation unter `AppData\Local\SurrealDB`. Parallel zeigt Scoop `current` filesystem-seitig auf **3.3.4**.

Damit darf `surreal version` ohne vorherige Pfad-/Binary-Festlegung **nicht** als Beweis für die Version des konfigurierten Docker-Servers behandelt werden. Launcher-Version, Scoop-Version und Server-Version sind drei getrennte Fakten.

## Kanonische Deployment-Konfiguration

Claire definiert den Context-Sidecar in:

- `infrastructure/compose/surrealdb.yml`
- `infrastructure/compose/surrealdb-dev.yml`

Die beobachtete Konfiguration lautet:

```text
service/container: cdb_surrealdb
image:             surrealdb/surrealdb:latest
bind intern:       0.0.0.0:8000
dev bind host:     127.0.0.1:8010 -> 8000
storage:           surrealkv:/data/surrealdb
volume:            surrealdb_data:/data
health probe:      /surreal is-ready -e ws://127.0.0.1:8000
```

Das beschreibt das **Soll-Deployment**. Weil Docker offline ist, sind Container-Metadaten, tatsächlich verwendeter Image-Digest, tatsächlich gemountetes Volume und tatsächliche Server-Version aktuell nicht belegbar.

## Namespace / Database

Die lokale, gitignorierte Query-Konfiguration ist vorhanden und weist auf:

```text
surreal_url: http://127.0.0.1:8010
namespace:   cdb_context_local
database:    cdb_context_intel
read_only:   true
```

Klassifikation:

- konfigurierter Namespace: `cdb_context_local`
- konfigurierte Database: `cdb_context_intel`
- DB-backed Existenz beider Werte: `UNAVAILABLE`

## Konfigurierte Context-Tabellen

Die lokale Query-Allowlist enthält derzeit:

```text
repo_artifact
doc_page
doc_section
doc_chunk
code_symbol
import_reference
test_case
config_reference
doc_code_link
dependency_edge
evidence_ref
claim
decision_event
agent_memory
```

Diese Liste ist **keine Schema-Inventur**. Ohne erreichbaren Endpoint können `INFO FOR DB`, `INFO FOR TABLE` und Record Counts nicht sicher ausgeführt werden.

### #21-State-Klassen

| State-Klasse | Config-Hinweis | DB-backed Status |
|---|---|---|
| `agent_memory` | in Query-Allowlist | `UNAVAILABLE` |
| `shared_memory` | nicht in Query-Allowlist | `UNAVAILABLE` — nicht als `ABSENT` interpretieren |
| `evidence` | nicht in Query-Allowlist | `UNAVAILABLE` — nicht als `ABSENT` interpretieren |
| `evidence_ref` | in Query-Allowlist | `UNAVAILABLE` |
| `claim` | in Query-Allowlist | `UNAVAILABLE` |
| `audit_observation` | nicht in Query-Allowlist | `UNAVAILABLE` — nicht als `ABSENT` interpretieren |

Damit existiert **kein** DB-backed Beweis für Records, Counts, Felder oder Indexes dieser Klassen.

## Versioning / Retention / System Time

Im kanonischen Claire-Repo wurden keine Konfigurationstreffer für folgende Runtime-Schalter gefunden:

```text
SURREAL_DATASTORE_VERSIONED
SURREAL_DATASTORE_RETENTION
versioned
retention
```

Die Compose-Start-Command setzt ebenfalls keine Versioning-/Retention-Flags.

Klassifikation:

- konfigurierte Versioning-/Retention-Semantik: `UNSPECIFIED`
- tatsächliche Runtime-Fähigkeit für `VERSION`: `UNAVAILABLE`
- `VERSION`-Smoke: **nicht ausgeführt**, weil kein sicherer Clone/Scratch des tatsächlichen Datastores und keine verifizierte Server-Version verfügbar sind

`system_as_of` aus #37 bleibt deshalb zunächst reine Read-/Storage-Metadatum-Semantik. #10 darf daraus noch keine SurrealDB-`VERSION`-Fähigkeit ableiten.

## Backup / Export

Die verifizierte lokale CLI 2.6.0 bietet den read-only Export-Befehl:

```text
surreal export --endpoint <ENDPOINT> --namespace <NAMESPACE> --database <DATABASE> <FILE>
```

Es wurde **kein Export ausgeführt**, weil der Endpoint offline ist und #38 keine Migration startet.

Vor einer späteren Migration muss der konkrete Export-Befehl an die **tatsächlich verifizierte Server-/CLI-Major-Version** gebunden und auf einer isolierten Restore-Zielinstanz geprüft werden. Die Existenz des 2.6.0-CLI-Befehls ist kein Beweis, dass der unbekannte Docker-Server 2.6.x verwendet.

## Migration / Rollback — aktivierte Risiken

Aktuell wird **keine** der versionsspezifischen Migrationsstrecken als tatsächlich notwendig markiert, weil die Server-Version unbekannt ist.

| Risiko | Status |
|---|---|
| 2.x → 3.x | `CONDITIONAL / SERVER_VERSION_UNKNOWN` |
| 3.2 → 3.3 Datastore-Migration / Rollback | `CONDITIONAL / SERVER_VERSION_UNKNOWN` |
| SurrealMX / `mem://` ohne VERSION | `NOT_INDICATED_BY_CONFIG` — Compose konfiguriert SurrealKV |
| Start eines beweglichen `latest` gegen bestehenden Datastore | `ACTIVE_RISK` |

Daraus folgt die zentrale Sicherheitsregel dieser Baseline:

> Den konfigurierten `cdb_surrealdb`-Container nicht allein für Inventarisierungszwecke starten, solange tatsächliches Image/Server-Version und Datastore-Sicherungsweg nicht kontrolliert sind.

## Wirkung auf #10 und #21

### #10 — SurrealDB Read Runtime

#10 kann weiterhin gegen Fixtures und die #39-Boundary entwickelt werden. Es darf jedoch **keine** lokale DB als `DB-backed` melden, solange Endpoint-/Server-Evidence fehlt. Storage-/VERSION-Fähigkeiten bleiben Capability-Gates.

### #21 — State Migration Gate

#21 erhält aus #38 derzeit ausschließlich:

- Deployment-Config-Evidence,
- den konfigurierten Namespace/DB-Namen,
- die Config-Allowlist,
- und den expliziten Status `UNAVAILABLE` für tatsächlichen Primary State.

#21 darf daraus weder `EMPTY` noch `ABSENT` ableiten. `STATE_HANDOFF_GO` bleibt blockiert, bis echter guarded read-only DB-Evidence vorliegt.

## Acceptance-Matrix #38

| Acceptance | Status |
|---|---|
| tatsächliche Server-Version DB-/Endpoint-backed | `BLOCKED — RUNTIME_OFFLINE` |
| lokale CLI-/Launcher-Version dokumentiert | `DONE` |
| Deployment-Modell / Storage Engine belegt oder unavailable | `DONE — CONFIGURED SurrealKV / RUNTIME UNAVAILABLE` |
| Namespace / Database belegt oder unavailable | `DONE — CONFIGURED / DB-BACKED UNAVAILABLE` |
| Tabellen / Felder / Indexes read-only inventarisiert | `BLOCKED — DB-BACKED UNAVAILABLE` |
| #21 Record Counts klassifiziert | `DONE — alle DB-backed UNAVAILABLE` |
| Versioning / Retention dokumentiert | `DONE — CONFIG UNSPECIFIED / RUNTIME UNAVAILABLE` |
| VERSION-Smoke auf sicherem Clone/Scratch oder unsupported | `BLOCKED — kein sicherer DB-backed Clone/Scratch` |
| Backup-/Export-Pfad dokumentiert | `DONE — CLI 2.6 export capability; kein Export ausgeführt` |
| Versionsrisiken nur bei realer Relevanz aktiviert | `DONE` |
| keine Secrets materialisiert | `DONE` |
| klare evidence-backed Baseline für #10/#21 | `DONE — Runtime-Unavailability ist selbst der zentrale Befund` |

## Abschlusszustand

`BASELINE_CAPTURED / RUNTIME_OFFLINE_BLOCKER`

#38 darf erst `DONE_MERGED_CLOSED` werden, wenn die drei blockierten DB-backed Punkte nachgeholt wurden, **ohne** einen unbekannten Datastore durch einen unkontrollierten Start zu migrieren.
