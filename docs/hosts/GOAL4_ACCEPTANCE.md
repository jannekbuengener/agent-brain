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
| Installation / Registration | PASS | PASS | PASS (native MCP-Discovery) | PASS (Discovery) |
| Fünf Capabilities im echten Host | PASS | PASS (0.3.4) | FAIL | FAIL |
| Fehler im echten Host | PASS (invalid_input) | PASS (invalid_input / contract_version_mismatch) | FAIL | FAIL |
| Fresh Host vollständig | PASS (akzeptierte Owner-Evidence) | FAIL | FAIL | FAIL |
| Upgrade + Restart/Reconnect + health | FAIL | FAIL | FAIL | FAIL |
| Rollback + Restart/Reconnect + health | FAIL | FAIL | FAIL | FAIL |

Die bestehenden Distribution-Tests prüfen tatsächlich isolierte Wheel-Installation
und Upgrade/Rollback eines neutralen Consumers. Host-Tests prüfen portable
Registrierung und exakte Upgrade-/Rollback-Pläne. Das belegt noch keinen
Restart/Reconnect jeder Host-Anwendung nach einem Versionswechsel.

## Neue reale Host-Evidence

Nach ausdrücklicher Owner-Freigabe wurde Cursor-MCP im isolierten Workspace
aktiviert. Natives `mcp list-tools agent-brain` entdeckt genau fünf Tools.
Die konkrete Übertragung des Testprompts und der read-only MCP-Antworten an
Cursor wurde anschließend ebenfalls ausdrücklich freigegeben. Der echte
Fünf-Call-Smoke scheitert jedoch vor den Calls an Windows Application Control:
Die native Cursor-Agent-Datei `file_service.win32-x64-msvc.node` im
Versionsverzeichnis `2026.08.25-3e8eec8` wird blockiert. Es wurde keine
Sicherheitsrichtlinie geändert und keine Sperre umgangen.
`CURSOR_REAL_HOST_SMOKE_REQUIRED` bleibt offen; aus Discovery folgt kein
Capability- oder Version-PASS im echten Host.

Für Claude wurden Testprompt und read-only MCP-Antworten ebenfalls ausdrücklich
freigegeben. Nach dem Owner-Login hat Claude Code 2.1.104 alle fünf Capabilities
auf `0.3.4` real ausgeführt. Session:
`b1498ff7-b1a5-4af7-9d52-d091efc07ae6`. Der beobachtete strukturierte Tool-Stream
belegt Protocol-/Capability-Schema, `read_only=true`, unveränderte CDB-Identität,
Source Priority sowie die bekannten degradierten/leeren Zustände. Evidence
blieb `NO_EVIDENCE` / `confirmed=false`; `briefing(task + topic)` wurde mit
`invalid_input` abgewiesen.

Claude wählte anfangs fälschlich `contract_version=1.0`. Der Server wies dies
mit `contract_version_mismatch` ab; der Host wiederholte erfolgreich mit
`agent-brain-cdb-context-capability/v1`. Das ist ein beobachtetes Host-Input-Finding,
keine neue Contract-Variante. Nach einer Chat-Unterbrechung war der Prozess-Handle
nicht mehr vorhanden. Die realen Tool-Antworten sind belegt; ein finaler
Prozess-Exit oder Kostenwert wurde nicht beobachtet und wird nicht behauptet.

Der neuere [Issue-Nachweis](https://github.com/jannekbuengener/agent-brain/issues/73#issuecomment-6556381157)
dokumentiert beide Host-Ergebnisse.

Für OpenCode wurde die konkrete Übertragung des Testprompts und der read-only
MCP-Antworten an OpenAI ebenfalls ausdrücklich freigegeben. OpenCode 1.1.20
führte den Smoke mit `openai/gpt-5.2` und einer temporären MCP-Konfiguration aus:
alle Tools gesperrt, ausschließlich `agent-brain*` erlaubt. Der Prozess endete
vor erfolgreichen Capability-Aufrufen mit Exit 1 und `Token refresh failed: 401`.
Session: `ses_e69766e34ffeFIAGDMm3dAEf4C`. Die erneute lokale OpenAI-Anmeldung
in OpenCode wurde angefragt. Daraus folgt kein Host-Capability-PASS.
Der [neueste Issue-Nachweis](https://github.com/jannekbuengener/agent-brain/issues/73#issuecomment-6556415627)
dokumentiert diesen Versuch und den Cursor-Signaturbefund.

## Verbleibende Abnahme

Echte lokale Host-Smokes sowie pro Host Upgrade-/Rollback-Reconnect nachweisen.
Erst danach finale Matrix und Evidence aktualisieren, finalen CI-/Main-Stand
prüfen, Abschlusskommentar auf #73 schreiben und das Issue manuell schließen.
Bis dahin: `BLOCKED_HOST_INSTALL / BLOCKED_OPENCODE_AUTH / BLOCKED_FINAL_ACCEPTANCE`, `NOT_GRANTED`.

Bekannte degradierte Zustände bleiben zulässig: fehlende Required-Read-Availability,
leere Search ohne Records und optionale unavailable Backends. Fehlende Evidence
bleibt `NO_EVIDENCE` / `confirmed=false`.
