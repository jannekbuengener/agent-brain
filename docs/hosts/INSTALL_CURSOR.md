# Install — Cursor

1. Install Agent Brain: `python -m pip install "agent-brain==0.3.4"`
2. Register the Agent Plugin directory `hosts/cursor/agent-brain/` in Cursor (Agent Plugins format: root `plugin.json` + `mcp.json` + `skills/`).
3. Confirm MCP server `agent-brain` and the five bounded tools.
4. Skill `agent-brain-cdb-context` should be discoverable from the plugin.

Capability semantics: [CDB_CONTEXT_CONTRACT.md](../capabilities/CDB_CONTEXT_CONTRACT.md).
