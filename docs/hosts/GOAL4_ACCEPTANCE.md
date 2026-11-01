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
| Fünf Capabilities im echten Host | PASS | PASS (0.3.4) | FAIL | PASS (0.3.4) |
| Fehler im echten Host | PASS (invalid_input) | PASS (invalid_input / contract_version_mismatch) | FAIL | PASS (invalid_input) |
| Fresh Host vollständig | PASS (akzeptierte Owner-Evidence) | FAIL | FAIL | FAIL |
| Upgrade + Restart/Reconnect + health | FAIL | PASS (0.3.3 → 0.3.4) | FAIL | PASS (0.3.3 → 0.3.4) |
| Rollback + Restart/Reconnect + health | FAIL | PASS (0.3.4 → 0.3.3) | FAIL | PASS (0.3.4 → 0.3.3) |

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
Der konkrete Cursor-Blocker wird auf Owner-Auftrag in [#86](https://github.com/jannekbuengener/agent-brain/issues/86)
verfolgt. Der Owner bestätigt, dass Cursor derzeit nicht funktioniert. #86 ersetzt
keinen Cursor-PASS und keine Final-Abnahme unter #73.

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

Der anschließende Claude-Lifecycle-Smoke baute beide exakten Tag-Snapshots als
Wheels und installierte sie in einer isolierten virtuellen Umgebung. Drei neue
Claude-Host-Prozesse lasen jeweils `health` und `evidence` real zurück:
initial `0.3.3`, nach Upgrade `0.3.4`, nach Rollback wieder `0.3.3`.
Alle drei Prozesse endeten mit Exit 0 und `is_error=false`; die erwarteten
Versionen wurden jeweils bestätigt. Evidence blieb `NO_EVIDENCE` / `confirmed=false`.
Keine Encoding-Env-Workarounds; die temporäre Runtime wurde abschließend auf
`0.3.4` zurückgestellt. Kosten der drei Lifecycle-Prozesse: `0.08656125 USD`.
Die Session-IDs stehen im maschinenlesbaren Record. Der Test nutzt eine bestehende
authentifizierte Claude-Installation; eine vollständig neue Host-Installation
wird damit nicht behauptet.

Für OpenCode wurde die konkrete Übertragung des Testprompts und der read-only
MCP-Antworten an OpenAI ebenfalls ausdrücklich freigegeben. Der erste Versuch
mit OpenCode 1.1.20 endete mit `Token refresh failed: 401`; nach dem Owner-Login
war dies behoben. Die vom alten Host angebotenen Modelle wurden danach vom
ChatGPT-Konto abgelehnt. Eine offizielle OpenCode-1.19.5-Installation wurde
isoliert temporär erstellt; die vorhandene 1.1.20-Installation blieb unverändert.

Mit `openai/gpt-6.1-sol` führte OpenCode 1.19.5 alle fünf Capabilities erfolgreich
auf Agent Brain `0.3.4` aus; `briefing(task=x, topic=y)` lieferte `invalid_input`.
Alle anderen Tools waren gesperrt, ausschließlich `agent-brain*` erlaubt.
Session: `ses_e696c44aaffeBPSxC4o0W4IMio`, Prozess-Exit 0.
Die sechs vollständigen strukturierten Antworten wurden aus dem gespeicherten
Host-Stream geparst und für identische Inputs mit dem gemeinsamen Core verglichen:
vollständige Response-Parität PASS. Evidence blieb `NO_EVIDENCE` / `confirmed=false`.
Der [neuere Issue-Nachweis](https://github.com/jannekbuengener/agent-brain/issues/73#issuecomment-6556540738)
dokumentiert den erfolgreichen OpenCode-Smoke und den Claude-Lifecycle.

Auch OpenCode führte den anschließenden Lifecycle real erfolgreich aus:
separate virtuelle Umgebung mit exakten Wheels, initial `0.3.3`, Upgrade
`0.3.4`, Rollback `0.3.3`; jeweils neuer Host-Prozess und tatsächliche
`health`-/`evidence`-Antworten mit der richtigen Version. Alle drei Exit 0 mit
terminalem `stop`; fehlende Evidence blieb unbestätigt. Die temporäre Runtime
wurde wieder auf `0.3.4` gestellt. Die Session-IDs stehen im Evidence-Record.
Keine bestehende Installation wurde ersetzt; keine vollständig neue
Host-Workstation oder neue Account-Anmeldung wird daraus abgeleitet.

## Verbleibende Abnahme

Echte lokale Host-Smokes sowie pro Host Upgrade-/Rollback-Reconnect nachweisen.
Erst danach finale Matrix und Evidence aktualisieren, finalen CI-/Main-Stand
prüfen, Abschlusskommentar auf #73 schreiben und das Issue manuell schließen.
Bis dahin: `BLOCKED_HOST_INSTALL / CURSOR_REAL_HOST_SMOKE_REQUIRED / BLOCKED_FINAL_ACCEPTANCE`, `NOT_GRANTED`.

Bekannte degradierte Zustände bleiben zulässig: fehlende Required-Read-Availability,
leere Search ohne Records und optionale unavailable Backends. Fehlende Evidence
bleibt `NO_EVIDENCE` / `confirmed=false`.
