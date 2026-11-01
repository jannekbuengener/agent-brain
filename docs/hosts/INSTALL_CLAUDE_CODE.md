# Install — Claude Code

1. Install Agent Brain: `python -m pip install "agent-brain==0.3.4"`
2. Ensure `agent-brain-mcp` starts (stdio; used by the plugin `.mcp.json`).
3. Add the local marketplace and install:

```bash
claude plugin marketplace add ./hosts/claude-code
claude plugin install agent-brain@agent-brain-local
```

4. Or load for development: `claude --plugin-dir ./hosts/claude-code/plugins/agent-brain`
5. Confirm MCP tools: `agent_brain.health`, `cdb_context.briefing`, `cdb_context.search`, `cdb_context.required_reads`, `cdb_context.evidence`.

Capability semantics: [CDB_CONTEXT_CONTRACT.md](../capabilities/CDB_CONTEXT_CONTRACT.md).
