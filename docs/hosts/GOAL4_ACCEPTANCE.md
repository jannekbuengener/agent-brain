# #73: finale Host-Abnahme

Stand: 2026-11-01. `NOT_GRANTED` — #73 bleibt offen.
Der maschinenlesbare Nachweis liegt unter
[Goal-4-Evidence](../evidence/agent_brain_issue73_goal4.v1.json).

## Gemeinsamer Capability-/Transport-Vertrag

Die bestehende Suite prüft alle vier Hostlabels am gemeinsamen MCP-Kern.
Zusätzlich werden die tatsächlichen stdio-Kommandos aus den drei lokalen
Host-Konfigurationen aus einem isolierten Arbeitsverzeichnis gestartet.
Die HTTP-Suite prüft den gemeinsamen ChatGPT-Remote-Transport separat.
Das sind automatisierte Capability-/Transport-Nachweise, keine vier gestarteten Host-Anwendungen.

| Capability / Contract | ChatGPT | Claude Code | Cursor | OpenCode |
|---|---|---|---|---|
| health | PASS | PASS | PASS | PASS |
| briefing | PASS | PASS | PASS | PASS |
| search | PASS | PASS | PASS | PASS |
| required_reads | PASS | PASS | PASS | PASS |
| evidence | PASS | PASS | PASS | PASS |
| structured failure | PASS | PASS | PASS | PASS |
| read-only | PASS | PASS | PASS | PASS |
| version/contract | PASS | PASS | PASS | PASS |

Der semantische Vergleich umfasst Protocol-/Capability-Version, Profil und
Source Priority, Limitations, Evidence-Status, Required-Read-Identität,
Briefing-Inhalt und strukturierte Fehler. Host-Rendering wird damit nicht geprüft.

## Tatsächliche Host-Abnahme

`FAIL` bezeichnet hier ein nicht erfülltes Nachweis-Gate, keinen behaupteten
Defekt der Capability. ChatGPT-PASS stammt aus der akzeptierten
[Owner-Evidence](https://github.com/jannekbuengener/agent-brain/issues/73#issuecomment-6556040954);
ein neuer manueller Marathon ist nicht erforderlich.

| Nachweis | ChatGPT | Claude Code | Cursor | OpenCode |
|---|---|---|---|---|
| Installation / Registration | PASS | PASS (bisheriger Install-Smoke) | FAIL | PASS (Discovery) |
| Fünf Capabilities im echten Host | PASS | FAIL | FAIL | FAIL |
| Fehler im echten Host | PASS (invalid_input) | FAIL | FAIL | FAIL |
| Fresh Host vollständig | PASS (akzeptierte Owner-Evidence) | FAIL | FAIL | FAIL |
| Upgrade + Restart/Reconnect + health | FAIL | FAIL | FAIL | FAIL |
| Rollback + Restart/Reconnect + health | FAIL | FAIL | FAIL | FAIL |

Die bestehenden Distribution-Tests prüfen tatsächlich isolierte Wheel-Installation
und Upgrade/Rollback eines neutralen Consumers. Host-Tests prüfen portable
Registrierung und exakte Upgrade-/Rollback-Pläne. Das belegt noch keinen
Restart/Reconnect jeder Host-Anwendung nach einem Versionswechsel.

Cursor CLI meldet beim frischen `list-tools agent-brain` fehlende MCP-Freigabe.
`mcp enable` mit `--workspace` findet die Konfiguration nicht. Der Versuch direkt
aus dem temporären Workspace wurde vor Ausführung von Auto-Review abgelehnt:
mögliche dauerhafte globale Cursor-Freigabe. Die explizite Owner-Zustimmung
steht aus; die Ablehnung wird nicht umgangen.

Auch der native Claude-Code-Smoke wurde vor Ausführung von Auto-Review
abgelehnt: Testprompt und MCP-Antworten würden an den externen Claude-Dienst
übermittelt; die Prüfung verlangt dafür eine ausdrückliche Payload-/Ziel-Freigabe.
Diese Owner-Zustimmung wurde ebenfalls angefragt. Der Smoke wurde nicht ausgeführt.

## Verbleibende Abnahme

Echte lokale Host-Smokes sowie pro Host Upgrade-/Rollback-Reconnect nachweisen.
Erst danach finale Matrix und Evidence aktualisieren, finalen CI-/Main-Stand
prüfen, Abschlusskommentar auf #73 schreiben und das Issue manuell schließen.
Bis dahin: `BLOCKED_HOST_INSTALL / BLOCKED_FINAL_ACCEPTANCE`, `NOT_GRANTED`.

Bekannte degradierte Zustände bleiben zulässig: fehlende Required-Read-Availability,
leere Search ohne Records und optionale unavailable Backends. Fehlende Evidence
bleibt `NO_EVIDENCE` / `confirmed=false`.
