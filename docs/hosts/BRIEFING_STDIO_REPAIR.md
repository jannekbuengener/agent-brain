# Briefing: Reparatur des synchronen stdio-Pfads (#73)

Historischer Reparaturnachweis für `0.3.3` / PR #82. Der nachfolgende
[Goal-3-Abschluss](https://github.com/jannekbuengener/agent-brain/issues/73#issuecomment-6556040954)
belegt die erfolgreichen ChatGPT-Owner-Smokes und den zusätzlichen UTF-8-Fix
aus PR #83 in `0.3.4`. Die folgenden damaligen Release-/Abnahmeaussagen sind historisch.

## Befund und Nachweis

Der vom Owner gemeldete ChatGPT-Aufruf lief über `agent-brain-mcp` (stdio,
ohne Argumente und ohne Port), nicht über HTTP oder Cloudflare. Der fachliche
Input war `Agent Brain Multi-Surface Plugin / GitHub Issue #73 / ChatGPT Integration`.
Der rohe Host-Payload und ein Stacktrace des ursprünglichen 300-s-Timeouts
liegen nicht vor; `task`, `topic` und `task_scope` werden deshalb getestet.

Der lokale Python-3.14-stdio-Reproducer hängt vor der Reparatur in:

```text
McpStdioServer.handle_message
  -> CapabilityMcpTransport.call_tool_mcp_result
  -> CapabilityGateway.invoke
  -> invoke_briefing
  -> ProtocolGateway.invoke_sync
  -> asyncio.run / new_event_loop
  -> ProactorEventLoop._make_self_pipe
  -> socket._fallback_socketpair
  -> socket.accept
```

Der Stack wurde nach drei Sekunden ausgegeben; der Diagnoseprozess wurde nach
sieben Sekunden begrenzt beendet. Außerhalb der eingeschränkten Umgebung
antwortet der installierte 0.3.2-stdio-Launcher auf Initialize, Health,
Required Reads und Briefing zusammen in ungefähr 1,1 Sekunden.

Das ist ein nachgewiesener reproduzierbarer Blockierpfad, keine nachträgliche
Stack-Evidence aus dem ursprünglichen ChatGPT-Aufruf. Ob dessen Timeout genau
dort entstand, muss der erneute Owner-Smoke bestätigen.

## Aufgerufene Operationen und ausgeschlossene Backend-Pfade

`briefing` komponiert ausschließlich Protocol `context_read` mit `mode=briefing`.
Diese Operation ruft den synchronen `build_briefing` mit `context_package=None`
auf. Sie führt keine Knowledge-/Memory-/SurrealDB-Abfrage, Live-Revalidation,
GitHub-/Netzwerkanfrage, Retry oder externe Subprozessoperation aus.
Der Event-Loop-Aufbau war eine unnötige Transportvoraussetzung.

`required_reads` ruft direkt den synchronen Resolver auf und benötigt diese
Brücke nicht. `health` verwendet dagegen dieselbe Async-Brücke und danach die
Backend-Health-Operationen. Deshalb kann aus dem zuvor erfolgreichen Health-Call
kein briefing-spezifischer Backend-Fehler abgeleitet werden. Im lokalen
eingeschränkten stdio-Reproducer blockiert auch Health vor seiner Fachlogik.

## Reparatur und Failure-Budget

`ProtocolGateway.invoke_sync` führt ausschließlich `context_read` direkt über
denselben synchronen Handler aus, den auch der Async-Dispatcher verwendet.
Request-Prüfung, Fehlerklassifikation, Redaction und Response-Erzeugung werden
von beiden Wegen geteilt. Andere Backend-Operationen bleiben unverändert.

Für diesen Pfad ist kein zusätzlicher externer Call vorhanden, der einen
internen Timeout benötigt: Die blockierende Betriebssystemvoraussetzung wird
vollständig vermieden. Backend-Probes werden auch nicht als neue Voraussetzung
eingeführt. Blockierende Backend-Doubles werden von Briefing nicht aufgerufen.
Der Subprozess-Regressionstest lässt `socketpair` 60 Sekunden blockieren und
verlangt trotzdem eine Briefing-Antwort innerhalb von fünf Sekunden.

Die request-only Ausgabe meldet `partial_source_state` und bei fehlenden
Evidence-Referenzen zusätzlich `no_evidence`. Eine Backend-Verfügbarkeit wird
weder behauptet noch aus leeren Ergebnissen abgeleitet. Vollständige,
fixture-basierte Domain-Briefings mit Context Package bleiben unverändert.

## Required-Reads-Finding

Der bestehende Resolver setzt ohne injizierte `available_paths` ausdrücklich
`available=false` und `warning=availability_not_provided`. Der Capability-Composer
reicht diese Werte durch; er definiert keinen aggregierten State und keine
aggregierte Limitation. Die aktuelle Shared-Host-Suite verlangt diese Ergänzung
nicht. Dieses Verhalten bleibt hier unverändert; eine aggregierte Darstellung
ist ein separates Finding unter #73, keine nachgewiesene Resolver-Regression.

## Validierung und verbleibende Grenze

Die Regression prüft alle drei Input-Aliasse mit unavailable, einzelnen
unavailable, blockierenden und gesunden Backend-Fixtures. Zusätzlich werden
stdio als echter Subprozess, Sync-/Async-Parität für valide und fehlerhafte
Requests, Evidence-Weitergabe und der unveränderte Domain-Briefing-Test geprüft.
Shared-Host-, MCP-, Capability- und Goal-2-Hosttests bleiben Pflicht.

Der Release-Pin ist `agent-brain==0.3.3` / `v0.3.3`. Der Tag darf erst nach
Merge und erfolgreicher Post-Merge-CI auf den verifizierten Main-SHA zeigen.
PR und Release sind keine neue ChatGPT-Host-Abnahme. #73 bleibt offen und
Goal 3 bleibt `NOT_GRANTED`, bis der Owner den echten ChatGPT-Smoke wiederholt.
