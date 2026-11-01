# Troubleshooting — Host Surfaces

## MCP does not start

- Confirm package import with the **same** interpreter you intend to use: `python -c "import agent_brain; print(agent_brain.__version__)"`
- ChatGPT cannot reach local MCP: prefer Secure MCP Tunnel; confirm `tunnel-client` `/readyz` and workspace association. Do not claim PASS without a real ChatGPT tool call.
- ChatGPT tools look stale after a schema change: connection → **Refresh**, then start a new conversation.
- MCP Inspector fails on `/mcp`: confirm `agent-brain-mcp-http` is listening and Accept headers include `application/json` / `text/event-stream`.
- Confirm console script: `agent-brain-mcp` (waits on stdio; Ctrl+C to stop)
- Fallback: `python -m agent_brain.mcp` — only if that `python` is the install environment
- On Windows with multiple Pythons, bare `python` may resolve to an interpreter **without** agent-brain → OpenCode/Claude show `Connection closed` / `ModuleNotFoundError`. Fix PATH or use `agent-brain-mcp` from the install's Scripts directory.

## Tools missing / wrong tools

Bei einem Windows-stdio-Timeout von `cdb_context.briefing`: siehe
[Diagnose und Reparatur ab 0.3.3](BRIEFING_STDIO_REPAIR.md). Der synchrone
Briefing-Pfad startet keinen Event-Loop; ein request-only Ergebnis bleibt
über `partial_source_state` / `no_evidence` als unvollständig erkennbar.

Only these five tools are registered: `agent_brain.health`, `cdb_context.briefing`, `cdb_context.search`, `cdb_context.required_reads`, `cdb_context.evidence`. Internal protocol operations are not published as host tools.

## `contract_version_mismatch`

Install a compatible Agent Brain pin. Do not silently ignore or downgrade.

## `backend_unavailable` looks like empty success

That would be a host bug. Failures must remain structured errors / `isError` results — never remap to `success: []`.

## Absolute path / checkout dependency

Host configs must use `agent-brain-mcp` (or the documented `python -m agent_brain.mcp` fallback) after a normal package install. If a config embeds a user home or drive-letter checkout path, reject it.

## Skill drift

Host skill copies must match `hosts/shared/skills/agent-brain-cdb-context/SKILL.md`. Fix by re-syncing from the canonical file; do not edit host forks independently.

## Claire / ChatGPT

Claire remains read-only evidence/source. Private ChatGPT MCP is not a dependency. ChatGPT app packaging is a later #73 goal.
