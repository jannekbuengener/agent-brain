# Install — OpenCode

1. Install Agent Brain: `python -m pip install "agent-brain==0.3.1"`
2. Install the skill into an OpenCode skill path (copy from `hosts/opencode/skills/agent-brain-cdb-context/` or the shared canonical skill).
3. Merge the MCP block from `hosts/opencode/opencode.agent-brain.mcp.example.json` into your OpenCode config (`command: ["agent-brain-mcp"]`).
4. Run `opencode mcp list` and confirm `agent-brain` is connected.
5. Exercise the five bounded tools.

Capability semantics: [CDB_CONTEXT_CONTRACT.md](../capabilities/CDB_CONTEXT_CONTRACT.md).
