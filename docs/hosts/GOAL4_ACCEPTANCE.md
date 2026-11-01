# #73: finale Host-Abnahme

Stand: 2026-11-01. Final Exit:
`AGENT_BRAIN_CDB_CONTEXT_MULTI_SURFACE_OPERATIONAL`
(Evidence-/Docs-PR noch mergen; #73 erst danach manuell schließen).

Maschinenlesbarer Nachweis:
[Goal-4-Evidence](../evidence/agent_brain_issue73_goal4.v1.json).

## Authority

`NO_NEW_AUTHORITY / EXECUTE_EXISTING_#73 / FINAL_CLOSEOUT_ONLY`

Distribution unverändert: `agent-brain==0.3.4` / immutable `v0.3.4` /
Release-SHA `4362b417a5c4a9a079b152a58781dbdb99cbc5af`. Kein neuer Runtime-Release.

## Fresh-Host-Reconciliation

#73 verlangt einen **frischen unterstützten Host** ohne Jannek-spezifische
absolute Package-Pfade sowie Fresh-Host-Install-Smoke. Das ist **nicht**
still als neue Workstation umgedeutet und auch nicht auf „nur neuer Prozess“
reduziert.

Akzeptierte Contract-Bedeutung (aus Issue-Wording + Install-Docs + Suite):

- clean isolated runtime/environment
- keine Owner-Absolutpfade in Package/Config
- fresh plugin/MCP registration
- fresh host process/session
- Install aus dokumentiertem Package-Pfad
- health-Readback + ein repräsentativer `cdb_context`-Call

Klassifikation:

| Host | Fresh-Host |
|---|---|
| ChatGPT | `FRESH_HOST_PASS` |
| Claude Code | `FRESH_HOST_PASS` |
| Cursor | `FRESH_HOST_PASS` |
| OpenCode | `FRESH_HOST_PASS` |

Frühere Matrix-Zeilen, die Fresh-Host als Workstation-FAIL führten, bleiben
historisch und sind durch diese Reconciliation ersetzt.

## Gemeinsamer Capability-/Transport-Vertrag

Automatisierte Suite prüft alle vier Hostlabels am gemeinsamen MCP-Kern.
Zusätzlich werden die stdio-Kommandos aus den lokalen Host-Konfigurationen
aus isoliertem CWD gestartet. HTTP-Suite prüft den ChatGPT-Remote-Transport.
Das sind automatisierte Capability-/Transport-Nachweise.

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

Semantischer Vergleich: Protocol-/Capability-Version, Profil/Source Priority,
Limitations, Evidence-Status, Required-Read-Identität, Briefing-Inhalt,
strukturierte Fehler. Host-Rendering wird nicht geprüft.

## Finale Vier-Host-Matrix

Nur `PASS` / `FAIL` / `BLOCKED`.

| Gate | ChatGPT | Claude Code | Cursor | OpenCode |
|---|---|---|---|---|
| Install / Register | PASS | PASS | PASS | PASS |
| Tool Discovery | PASS | PASS | PASS | PASS |
| health | PASS | PASS | PASS | PASS |
| briefing | PASS | PASS | PASS | PASS |
| search | PASS | PASS | PASS | PASS |
| required_reads | PASS | PASS | PASS | PASS |
| evidence | PASS | PASS | PASS | PASS |
| structured failure | PASS | PASS | PASS | PASS |
| version 0.3.4 | PASS | PASS | PASS | PASS |
| read-only | PASS | PASS | PASS | PASS |
| semantic parity | PASS | PASS | PASS | PASS |
| upgrade | PASS | PASS | PASS | PASS |
| rollback | PASS | PASS | PASS | PASS |
| restore 0.3.4 | PASS | PASS | PASS | PASS |
| fresh-host acceptance | PASS | PASS | PASS | PASS |
| no absolute owner paths | PASS | PASS | PASS | PASS |

## Real host evidence

### ChatGPT

Akzeptierte Owner-Evidence für den Fünf-Call-Smoke + `invalid_input` auf
ChatGPT Desktop:
[Goal-3 Closeout](https://github.com/jannekbuengener/agent-brain/issues/73#issuecomment-6556040954).

Lifecycle closeout über offizielle Codex/`mcp_servers.agent_brain`-Registration
mit neuen Sessions je Stufe, isolierten Tag-Wheels und tatsächlichem
Versions-Readback:

- initial `0.3.3` — `01a19740-5efb-75a2-84af-1304aec98ae2`
- upgrade `0.3.4` — `01a19741-02da-7142-99e9-5bc50a9d63fe`
- rollback `0.3.3` — `01a19741-a050-7283-8264-b33706e7fb0e`
- restore `0.3.4` — `01a19742-3b6f-7d50-8406-49333de5cb8d`

Owner-Restore ohne Encoding-Workaround:
Session `01a19743-d7ee-72d1-9ee3-5d54076af9d0`, `agent-brain==0.3.4`,
`PYTHONIOENCODING`/`PYTHONUTF8` aus der Owner-MCP-Config entfernt.

### Claude Code

Realer Fünf-Call-Smoke + Failure auf `0.3.4` und Lifecycle
`0.3.3 → 0.3.4 → 0.3.3` (Restore auf `0.3.4`) bereits belegt:
[Issue-Nachweis](https://github.com/jannekbuengener/agent-brain/issues/73#issuecomment-6556381157).
Keine unnötige Wiederholung in diesem Closeout.

### Cursor

#86 CLOSED. Root Cause war stale `cursor-agent` + WDAC; Resolution nur
offizielles Update auf `2026.10.22-27dcf5f`. Fünf-Call-Smoke PASS
(Session `80d502bb-30b6-4ddb-8f17-f903699511ea`).

Package-Lifecycle closeout mit isolierter Runtime und neuem
`cursor-agent`-Prozess je Stufe:

- initial `0.3.3` — `a8216c92-7e6a-43c2-968f-e3f6b9e9b90b`
- upgrade `0.3.4` — `54ed76c4-4f9e-4867-a72f-4311ee6ea0b9`
- rollback `0.3.3` — `bb29a97e-f698-4147-ab25-75eda864d23a`
- restore `0.3.4` — `1886fd3c-4922-416a-928e-bf1987d11c5f`

Keine Security-Policy geändert. Kein Bypass.

### OpenCode

Realer Fünf-Call-Smoke + Lifecycle bereits belegt:
[Issue-Nachweis](https://github.com/jannekbuengener/agent-brain/issues/73#issuecomment-6556540738)
und Folgetext. Keine unnötige Wiederholung.

## Automated shared transport evidence

- Shared capability/host packaging/parity suite
- Windows cp1252 → UTF-8 stdio regression auf `0.3.4`
- Secret-/Prompt-Injection-/read-only-Regressionen
- Absolute-Path-Scan der Host-Packages: 0 Hits

Closeout-fokussierte Auswahl vor Evidence-PR: 27 passed.

## Lifecycle evidence

| Host | Upgrade | Rollback | Restore | Encoding-Env nötig für 0.3.4 |
|---|---|---|---|---|
| ChatGPT | PASS | PASS | PASS | nein |
| Claude Code | PASS | PASS | PASS | nein |
| Cursor | PASS | PASS | PASS | nein |
| OpenCode | PASS | PASS | PASS | nein |

## Historical blockers

Als historisch markiert, nicht aktuell:

- `BLOCKED_CHATGPT_CUSTOM_MCP_PERMISSION`
- `BLOCKED_HOST_INSTALL` / `CURSOR_REAL_HOST_SMOKE_REQUIRED` (#86, inzwischen CLOSED)
- `CHATGPT_LIFECYCLE_RECONNECT_INCOMPLETE`
- `FRESH_HOST_ACCEPTANCE_INCOMPLETE`
- `BLOCKED_FINAL_ACCEPTANCE`

## Current blockers

Keine.

## Safety / Shared gates

- `read_only=true`
- keine Shell-/Filesystem-/GitHub-/Claire-/Trading-/Risk-/Kill-Switch-/Memory-Write-Surface
- Prompt-Injection bleibt Source Data
- SurrealDB optional unavailable bleibt out of scope / nonblocking

## Bekannte nonblocking Findings

- `required_reads`: `availability_not_provided`
- `search`: leere `candidates` ohne Records
- optionale knowledge/memory/surreal Backends unavailable

## Closeout-Hinweis

Evidence-PR verwendet `Refs #73` (nicht `Closes`/`Fixes`).
Parent bleibt bis zum manuellen Closeout nach Merge + Post-Merge-CI OPEN.
