# SurrealDB Runtime Baseline — 2026-10-31

**Issue:** #38  
**Status:** `BASELINE_CAPTURED / DOCKER_SCRATCH_DB_BACKED`  
**Vorgänger:** `docs/surrealdb/RUNTIME_BASELINE_2026-10-21.md` (`RUNTIME_OFFLINE_BLOCKER`)

## Zweck

Diese Baseline ersetzt den Offline-Blocker vom 2026-10-21 durch **Docker-gestützte, guarded Scratch-/Clone-Evidence**. Das Original-Volume wurde nicht mit einem SurrealDB-Prozess geöffnet. Alle DB-Reads liefen gegen einen isolierten Scratch-Clone.

## Guardrails dieses Inventars

- Docker Engine war verfügbar (`29.9.2`, Docker Desktop 4.97.0, context `desktop-linux`)
- Original-Volume `cdb_database_surrealdb_data` nur read-only gemountet (Alpine-Listing) bzw. byteweise nach Scratch kopiert
- SurrealDB-Start **nur** gegen Scratch-Volume `agent_brain_38_surrealdb_scratch_20261031`
- Image **digest-gepinnt**, nicht über bewegliches Tag gestartet:
  - `surrealdb/surrealdb@sha256:65000ff205b08363b035b457f292dc0a0b1cd4212935dd5ea94073cf67adf306`
  - verifizierte Binary: `3.0.4 for linux on x86_64` / HTTP `/version` → `surrealdb-3.0.4`
- Kein Start des Compose-Service `cdb_surrealdb` gegen das Original
- Keine Secrets in Issue-/Doc-Text materialisiert (Usernamen nur soweit runtime-sichtbar und nicht geheim)
- Scratch-Container nach Inventar gestoppt/entfernt; Scratch-Volume bewusst behalten

## Docker Discovery (read-only)

| Artefakt | Evidence | Klassifikation |
|---|---|---|
| Docker Engine | Client/Server `29.9.2` | `VERIFIED` |
| Laufende Container | keine | `EMPTY` |
| Gestoppte Container | `mirofish-sb`, `cdb-ci-4466-tls-run` — **kein** SurrealDB-Container | `VERIFIED` |
| Image `surrealdb/surrealdb:latest` | lokal = Digest `sha256:65000ff…` → **3.0.4** (Created 2026-03-13) | `VERIFIED / TAG_FLOATING_AT_PULL_TIME` |
| Image `surrealdb/surrealdb:v2.2.1` | `2.2.1 for linux on x86_64` | `VERIFIED` |
| Image `surrealdb/surrealist:latest` | vorhanden | `PRESENT / NOT_RUNTIME` |
| Volume `cdb_database_surrealdb_data` | Compose-Projekt `cdb_database`, Volume-Label `surrealdb_data`, Created `2026-03-19` | `VERIFIED` |
| Volume-Inhalt (RO) | `/data/surrealdb` SurrealKV (`LOCK`, `manifest`, `sstables`, `vlog`, `wal`), ~38.5 MiB | `VERIFIED` |
| Container am Volume | keiner (`docker ps -a --filter volume=…` leer) | `VERIFIED` |
| Dev-Endpoint `127.0.0.1:8010` vor/nach Inspect | offline | `UNAVAILABLE` (außer während Scratch-Fenster) |

### Kritischer Image-Befund

Lokales `surrealdb/surrealdb:latest` ist **nicht** unbestimmt: die aktuell geladene Schicht ist **3.0.4**. Ein Compose-Start mit Tag `latest` gegen das Original bliebe trotzdem riskant (Tag kann beim nächsten Pull wandern). Inventar nutzte deshalb den **festen Digest**.

## Scratch-/Clone-Pfad

```text
source:  cdb_database_surrealdb_data          (unangetastet für Surreal-Open)
clone:   agent_brain_38_surrealdb_scratch_20261031
method:  alpine `cp -a` from RO mount
verify:  Original nach Clone weiter ~40348736 bytes; SST-mtime unverändert
```

Scratch wuchs während des Inspects leicht (~8 KiB) und erhielt durch `USE NS/DB`-Proben zusätzliche **leere** Database-Definitionen unter `main`/`governance`. Das betrifft nur den Scratch, nicht das Original.

Für Auth-Inventar: Compose-`SURREALDB_ENV` authentifiziert **nicht** gegen den vorhandenen Root-User des Datastores. Scratch-Reads liefen deshalb temporär mit `--unauthenticated` und Bind `127.0.0.1:8010` — nur Scratch, nur Inventarfenster.

Runtime-sichtbarer Root-User im Datastore: `codex` (PASSHASH nicht dokumentiert).

## DB-backed Runtime-Evidence (Scratch)

| Bereich | Evidence | Klassifikation |
|---|---|---|
| Server-Version | `3.0.4` (Logs + `/version`) | `VERIFIED` |
| Storage Engine | `surrealkv:/data/surrealdb` geöffnet; Manifest `version=1`, `tables=4`, `last_sequence=2413187` | `VERIFIED` |
| SurrealKV Versioning | Startup: `Versioning enabled: false`, `retention: 0ns` | `VERIFIED_DISABLED` |
| Namespaces | `main`, `governance` | `VERIFIED` |
| Konfigurierter NS `cdb_context_local` | in `INFO FOR ROOT` **nicht** vorhanden | `ABSENT` |
| DB `governance/governance_mirror` | vorhanden | `VERIFIED` |
| DB `main/main` | vorhanden, keine Tabellen | `VERIFIED_EMPTY_SCHEMA` |

### Tabellen in `governance` / `governance_mirror`

| Tabelle | Typ | Felder (kurz) | Count | Indexes |
|---|---|---|---|---|
| `audit_trail` | SCHEMAFULL | `action_type`, `actor_id`, `created_at`, `integrity_*`, `payload`, `service_name` | **1** | keine |
| `governance_events` | SCHEMAFULL | `created_at`, `event_type`, `evidence_ref`, `integrity_*` | **1** | keine |
| `ledger_event` | SCHEMALESS | (keine definierten Felder) | **1** | keine |

Die drei Records sind Issue-639 Restore-Drill-Seeds (`*:issue639_pre`, `restore_drill_seed`, `2026-03-19`). Logischer Nutzinhalt ≈ Seed; On-Disk ~38.5 MiB enthält SurrealKV-/SST-Residue.

### Konfigurierte Context-DB vs. Realität

Claire Query-Config (weiterhin Config-Evidence):

```text
namespace: cdb_context_local
database:  cdb_context_intel
```

DB-backed im inventarisierten Volume:

```text
cdb_context_local     ABSENT
cdb_context_intel     nicht als vorbestehende DB im Original-Katalog belegt
                      (unter Scratch durch USE-Probe leer angelegt — Scratch-only)
```

### #21-State-Klassen (DB-backed gegen Scratch)

Geprüft in `governance/governance_mirror` und `main/main`:

| State-Klasse | DB-backed Status |
|---|---|
| `agent_memory` | `ABSENT` (Tabelle existiert nicht) |
| `shared_memory` | `ABSENT` |
| `evidence` | `ABSENT` |
| `evidence_ref` | `ABSENT` als Tabelle; Feld `evidence_ref` existiert auf `governance_events` |
| `claim` | `ABSENT` |
| `audit_observation` | `ABSENT` |

`ABSENT` hier heißt: **im inventarisierten Datastore nicht vorhanden**. Das ist kein Beweis, dass ein anderer, noch unentdeckter Primary-State woanders liegt — aber der eindeutig identifizierte Claire-Compose-Volume-Pfad enthält diese Klassen nicht.

Context-Allowlist-Tabellen (`repo_artifact`, `doc_page`, …) ebenfalls `ABSENT` in den geprüften DBs.

## VERSION-Fähigkeit

- SurrealKV startet mit **Versioning disabled**
- Smoke auf Scratch:

```text
SELECT * FROM audit_trail VERSION d"2026-05-01T00:00:00Z";
→ ERR: Invalid argument: Versioning not enabled
```

Klassifikation: `UNSUPPORTED_ON_THIS_DATASTORE` (belegt), nicht bloß `UNAVAILABLE`.

## Auth-/Start-Risiken (ops)

| Risiko | Status |
|---|---|
| Compose `image: surrealdb/surrealdb:latest` | Tag floatet; lokal aktuell 3.0.4 — Digest pinnen | `ACTIVE_RISK` |
| `SURREALDB_ENV` vs. Datastore-Root `codex` | Auth mit aktueller Env-Datei schlägt fehl (401) | `ACTIVE_BLOCKER_FOR_COMPOSE_START` |
| Blindstart Original mit `latest` | weiterhin untersagt; Scratch-Pfad ist der sichere Weg | `ACTIVE_POLICY` |
| 2.x→3.x Migration | lokaler Digest ist bereits 3.0.4; Datastore öffnete unter 3.0.4 auf Scratch ohne Migrationsfehler | `NOT_INDICATED_FOR_THIS_VOLUME` |
| 3.2→3.3 | Server ist 3.0.4, nicht 3.2/3.3 | `NOT_APPLICABLE_NOW` |

## Launcher-Evidence (unverändert relevant)

| Quelle | Version | Klassifikation |
|---|---|---|
| `AppData\Local\SurrealDB\surreal.exe` | `2.6.0 for windows on x86_64` | `VERIFIED` |
| Docker Image digest `65000ff…` | `3.0.4` | `VERIFIED_SERVER` |
| Docker Tag `v2.2.1` | `2.2.1` | `VERIFIED_IMAGE_ONLY` |

CLI 2.6.0 ≠ Server 3.0.4. Export-/Client-Befehle müssen an die Server-Major gebunden werden.

## Wirkung auf #10 / #21 / #67

### #10

- Darf die Server-Version **3.0.4** und SurrealKV ohne VERSION als belegte Capability-Lage konsumieren.
- Darf `cdb_context_local`/`cdb_context_intel` **nicht** als DB-backed existent melden.
- Fail-closed für fehlenden NS/DB und Auth-Mismatch bleibt Pflicht.

### #21

- Primary State auf dem identifizierten Volume ist **kein** Agent-Memory-/Evidence-/Claim-Corpus, sondern ein Governance-Mirror-Seed aus #639.
- #21-Klassen sind hier `ABSENT`, nicht `UNAVAILABLE`.
- `STATE_HANDOFF_GO` darf daraus **nicht** automatisch folgen: Owner muss entscheiden, ob dieses Volume der vorgesehene SurrealDB-primary für Agent Brain ist oder ob ein anderer State noch fehlt.
- Conservative helper bleibt `STATE_HANDOFF_BLOCKED` bei `unconfirmed`.
- Nach ELSEWHERE-Suche: `evidence_backed_handoff_2026_10_31()` → `STATE_HANDOFF_GO` / `confirmed_primary` / `NOOP_ABSENT` — siehe `docs/surrealdb/STATE_HANDOFF_DECISION_2026-10-31.md` und `local_runtime_truth_2026_10_31()`.

### #67

Runtime-Gate #38 ist für die drei früheren Offline-Blocker **evidence-backed nachziehbar**. Goal-Exit `SURREAL_READ_STATE_HANDOFF_GO` bleibt abhängig von #10/#21-Delivery und der Owner-Entscheidung zur State-Authority dieses Volumes.

## Acceptance-Matrix #38

| Acceptance | Status |
|---|---|
| tatsächliche Server-Version DB-/Endpoint-backed | `DONE — 3.0.4 (Scratch, pinned digest)` |
| lokale CLI-/Launcher-Version dokumentiert | `DONE` |
| Deployment-Modell / Storage Engine | `DONE — SurrealKV verified on scratch` |
| Namespace / Database | `DONE — main/governance verified; cdb_context_local ABSENT` |
| Tabellen / Felder / Indexes inventarisiert | `DONE — governance_mirror` |
| #21 Record Counts | `DONE — Klassen ABSENT; Mirror-Seeds count=1` |
| Versioning / Retention | `DONE — disabled / VERSION unsupported` |
| VERSION-Smoke auf Scratch | `DONE — Versioning not enabled` |
| Backup-/Export-Pfad dokumentiert | `DONE — kein Export ausgeführt` |
| Versionsrisiken konditional | `DONE — an 3.0.4 gebunden` |
| keine Secrets materialisiert | `DONE` |
| Original nicht blind mit `latest` geöffnet | `DONE` |

## Abschlusszustand

`BASELINE_CAPTURED / DOCKER_SCRATCH_DB_BACKED`

ELSEWHERE-Suche auf diesem Host fand keinen zweiten Claire-SurrealKV; Context-NS war nie angelegt. Auth-Abgleich `SURREALDB_ENV` ↔ Root-User `codex` bleibt ops-offen vor Compose-Start gegen Original.
