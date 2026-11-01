# Agent Brain Plugin / Capability Architecture

**Status:** Goal 1 under [#73](https://github.com/jannekbuengener/agent-brain/issues/73)  
**Paket:** `agent_brain.capabilities`  
**Capability:** `cdb_context`  
**Produktname:** `Agent Brain`

## Zielbild

```text
Agent Brain generic Core
        ↓
agent_brain.protocol          (#12)
        ↓
agent_brain.capabilities      (host-neutral Capability Layer)
        ↓
cdb_context Profile           (CDB-spezifisch, außerhalb generischem Core)
        ↓
host-neutral tool descriptors
        ↓
Future host adapters (ChatGPT / Claude Code / Cursor / OpenCode)
```

## Verbindliche Regel

> Host adapter = packaging / registration / transport / host UX.

Nicht:

> host adapter = separate fachliche Context implementation.

## Was Goal 1 liefert

- einen versionierten, hostneutralen Capability Contract
- Mapping der fünf Pflicht-Capabilities auf bestehende #12/#6/#7/#8 Surfaces
- CDB-Profil (Required Reads, Source Priority, Guardrails, Repo-Identity)
- gemeinsame Contract-Test-Suite (`tests/capabilities/test_host_contract_suite.py`) für spätere Host-Adapter
- keine Host-Pakete und keine zweite Public Protocol Surface

## Dokumente

- [cdb_context Contract](CDB_CONTEXT_CONTRACT.md)

## Versionierung

- Package-/Pin-Wahrheit bleibt #17 (`pyproject.toml` / `agent_brain.__version__` / Tag `vX.Y.Z`)
- Capability-Contract-Schema: `agent-brain-cdb-context-capability/v1`
- Contract-Version und Package-Version sind unterschiedliche Begriffe, aber keine konkurrierende Package Truth
