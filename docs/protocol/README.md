# CLI und Protocol Surface

**Status:** Slice 12 / [#12](https://github.com/jannekbuengener/agent-brain/issues/12)  
**Pakete:** `agent_brain.protocol` (Application Surface), `agent_brain.cli` (Transport)

## Zweck

Agent Brain unabhängig von Claire bedienbar machen. Externe Consumer nutzen eine schmale, versionierte, read-only Public Surface für zentrale Brain-Funktionen — ohne Core-Interna, ohne privaten ChatGPT-MCP und ohne Claire-Businesslogik.

## Architektur

```text
Agent Brain Core
        ↓
Application / Public Protocol Surface   (agent_brain.protocol)
        ↓
 ┌────────────┬──────────────────┬────────────────┐
 CLI          optional MCP       weitere Consumer
 (agent_brain.cli)  (mcp_adapter)
```

Adapter sind Transport. Fachlogik bleibt in den bestehenden Core-Paketen.

## Version

Die Surface bindet sich an die kanonische Package-Version aus #17:

- `agent_brain.__version__` / `importlib.metadata.version("agent-brain")`
- CLI: `agent-brain version`
- Protocol-Feld: `agent_brain_version`

Keine zweite Versionsquelle.

## Schnellstart

```bash
python -m pip install "agent-brain==0.3.4"
agent-brain version
agent-brain health --json
agent-brain capabilities --json
```

Programmatisch:

```python
from agent_brain.protocol import invoke

print(invoke("version").to_dict())
print(invoke("capabilities").to_dict())
```

## Operationen

| Operation | Bedeutung |
|---|---|
| `version` | Package-/Protocol-Metadaten |
| `health` | Core + Backend-Zustände (`available` / `unavailable` / `degraded`) |
| `capabilities` | reale Capability-Verfügbarkeit |
| `context_read` | Context Package / Briefing |
| `retrieval` | Hybrid Retrieval über gelieferte Index-Records |
| `evidence` | Trust-Summary (expliziter Scope) |
| `memory_read` | Memory Recall (gebundener Store + Scope) |
| `surreal_read` | Capability-Gate für Surreal-Read |

Write-/Remember-/Seed-/Repair-Operationen werden fail-closed abgelehnt.

## Fehler

Strukturierte Codes: `invalid_input`, `invalid_scope`, `unsupported_operation`, `capability_unavailable`, `backend_unavailable`, `contract_version_mismatch`, `internal_failure`.

`BACKEND_UNAVAILABLE` und `INVALID_SCOPE` sind niemals erfolgreiche leere Fachantworten.

## Optionaler MCP-Adapter

`agent_brain.protocol.tool_schemas` / `BrainMcpAdapter` sind host-neutral und benötigen kein MCP-SDK. Der Core bleibt ohne MCP installierbar und testbar. Privates ChatGPT-MCP ist ausgeschlossen.

Für Host-Surfaces (#73 Goals 2–3) existieren shared MCP-Entrypoints:

```bash
agent-brain-mcp
# fallback:
python -m agent_brain.mcp

agent-brain-mcp-http --host 127.0.0.1 --port 8787
# fallback:
python -m agent_brain.mcp.http
```

Sie exponieren nur die bounded `cdb_context`-Tools über `CapabilityGateway` und werden von den Host-Adaptern unter `hosts/` referenziert (stdio lokal; Streamable HTTP `/mcp` für ChatGPT/Inspector/Tunnel).

## Beziehung zu #13 / #17 / #73

- #17 liefert Pinning und Version; #12 konsumiert sie.
- #13 konsumiert diese Surface für den Claire-Cutover — ohne neue Interface-Architektur.
- #73 Goal 1 (`agent_brain.capabilities` / `cdb_context`) mappt hostneutrale Capability-Namen auf diese Protocol Surface; siehe [Capability Docs](../capabilities/README.md).
