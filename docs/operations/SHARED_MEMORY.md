# Agent Brain: gemeinsames Arbeitsgedächtnis (lokaler SurrealDB-Slice)

**Stand:** 2026-11-03. **Status:** LOCAL_TRUSTED_OPERATOR_SLICE + G1 consumer AuthN/AuthZ foundation ([#96](https://github.com/jannekbuengener/agent-brain/issues/96) / [#97](https://github.com/jannekbuengener/agent-brain/issues/97)).  
Consumer grants use protected token hashes and an external revoke denylist — see [SHARED_MEMORY_AUTH.md](SHARED_MEMORY_AUTH.md). MCP gateway and multi-repo host E2E remain later gates. No Remote-/Public-Bind without Owner approval.

## Ziel und Architektur

Agent A speichert einen Arbeitsstand mit Repo, Agent-ID, Task, Status, Zusammenfassung,
nächstem Schritt und Quellenverweis. Agent B liest diese Information in einer anderen
Session wieder. Speicherung ist append-only und über einen Idempotenzschlüssel vor
Dubletten geschützt. Neuere, geprüfte Git-/GitHub-Daten haben weiterhin Vorrang.

Diese Fähigkeit ergänzt die bestehenden schreibgeschützten `MemoryStore`-Contracts als
separate, ausdrücklich begrenzte `SurrealHandoffJournal`-Schreiboberfläche. Kein
NEXUS.MEMORY, keine automatische Reflection, keine Agent-Memory-/Spectron-API,
keine beliebigen Datenbank-Mutationen.

## Runtime-Ownership

- Compose: `infrastructure/compose/shared-memory.yml`
- Container: `agent_brain_surrealdb`, Compose-Projekt `agent_brain`
- Isoliertes Volume: `agent_brain_memory_data`
- NS/DB: `agent_brain/shared_memory`
- Port: `127.0.0.1:8012` (nur lokal)
- Image: SurrealDB 3.0.4, fixierter Digest
- CDBs `cdb_surrealdb`, Port 8010, Volume und Secrets bleiben unverändert.

**Lizenz:** SurrealDB-Kern ist BSL 1.1 (kostenlos selbst hostbar, aber nicht
OSI-konformes Open Source). Ein zusätzliches proprietäres Agent-Memory-Produkt
kommt hier nicht zum Einsatz.

## Einmalige Einrichtung

1. Unter `%USERPROFILE%\\Documents\\.secrets\\.agent-brain` eine Datei
   `SURREALDB_ENV` mit `SURREAL_USER=root` und
   `SURREAL_PASS=<separates starkes Passwort>` anlegen. Nie committen.
2. Diese Datei und den Ordner auf Maintainer und SYSTEM beschränken.
3. `AGENT_BRAIN_SECRETS_PATH` auf den absoluten Pfad zum Ordner setzen.
4. SurrealDB braucht für ein neu angelegtes Linux-Volume UID 65532:
   `docker volume create agent_brain_memory_data`
   `docker run --rm -u 0 -v agent_brain_memory_data:/data alpine:latest chown -R 65532:65532 /data`
5. Im Agent-Brain-Repo:
   `docker compose -p agent_brain -f infrastructure/compose/shared-memory.yml up -d`
   oder `powershell -File scripts/shared-memory.ps1 -Action start`. Das explizite `-p` ist Pflicht, weil in dieser Windows-Umgebung eine globale `COMPOSE_PROJECT_NAME`-Variable gesetzt sein kann.
6. Verifizieren: `docker ps --filter name=agent_brain_surrealdb`,
   `http://127.0.0.1:8012/health`.
7. CLI lokal installieren: `python -m pip install -e .`

Das Root-Passwort bleibt außerhalb des Repositories und wird nicht an Consumer
ausgegeben. `agent-brain-handoff` verwendet ausschließlich localhost:8012.

## Beispiel: Agent A schreibt

Schreibe `handoff.json` außerhalb des Git-Repositories:

```json
{
  "repository_ref": "jannekbuengener/agent-brain",
  "agent_id": "claude-code",
  "task_ref": "issue:123",
  "status": "in_progress",
  "summary": "Schema ist fertig. Tests sind grün; die Integration ist noch offen.",
  "next_step": "Integration testen und den aktuellen GitHub-Status erneut prüfen.",
  "source_ref": "github:issue:123",
  "idempotency_key": "issue-123-session-a-end"
}
```

`agent-brain-handoff write --payload-file handoff.json`

Das gleiche Kommando mit demselben Idempotenzschlüssel erzeugt keinen zweiten
Eintrag, solange die Inhalte identisch sind. Bei anderer Payload gibt es einen Fehler.

## Beispiel: Agent B liest

`agent-brain-handoff read --repo jannekbuengener/agent-brain --task issue:123`

Ohne `--task` werden die neuesten Einträge des Repositories angezeigt.
Leere Treffer gelten nur bei erreichbarer, erfolgreich abgefragter Datenbank
als leer. Ausfall der DB ist ein Fehler – kein erfolgreicher Leerstand.

## Sicherheits- und Produktgrenzen

- Nur typisierte append-/recall-Operationen, keine direkte SurrealQL-CLI nach außen.
- Kein repoübergreifendes Lesen ohne expliziten getrennten Aufruf.
- Die Legacy-CLI `agent-brain-handoff` bleibt die lokale Maintainer-Oberfläche mit
  Root-DB-Auth. Externe Consumer dürfen **keine** Root-Credentials erhalten.
- G1 führt serverseitige Consumer-Identitäten ein (`agent-brain-handoff-auth` +
  `HandoffGateway`): Token-Hashes, per-Repo Grants, Rotation/Widerruf und eine
  Revoke-Denylist außerhalb des Surreal-Volumes. Details: [SHARED_MEMORY_AUTH.md](SHARED_MEMORY_AUTH.md).
- Keine Secrets, personenbezogenen Daten oder produktiven Trading-Zustände eintragen.
- Statusmeldungen aus Memory ersetzen nicht den Live-Check von GitHub/Repo.
- Kein generischer `brain.write`-Pfad; keine produktive Agent-Memory-Adoption.
- Kein automatischer Agent-Write durch bloße Installation.

## Backup und Recovery

Das neue Volume gehört **nicht** zum bestehenden offiziellen Docker-Backup
vom 03.11.2026. Es besitzt einen **eigenen** Backup-Satz vom 03.11.2026
(`F:\Backups\Services\AgentBrain\2026\2026-11-03_183741`, 5/5 SHA-256,
isolierter Restore erfolgreich). Nachweis:
`F:\Backups\_docs\AGENT_BRAIN_SHARED_MEMORY_RESTORE_PROOF_2026-11-03.md`.
Für weitere Sicherungen: `powershell -File scripts/backup-shared-memory.ps1` erzeugt einen konsistenten Volume-Snapshot mit Manifest, Secrets und Prüfsummen auf `F:\Backups`. Vor dem Remote-/Multiuser-Cutover ist ein isolierter Restore-Nachweis erforderlich. Der Backup-Vorgang stoppt und startet nur den Agent-Brain-Datenbankcontainer, niemals CDB.
