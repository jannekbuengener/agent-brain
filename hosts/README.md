# Host Surfaces — Agent Brain / `cdb_context`

Parent: [#73](https://github.com/jannekbuengener/agent-brain/issues/73)  
Deliveries: Goal 2 (local hosts) · Goal 3 (ChatGPT remote MCP)

## Architecture

```text
                    Agent Brain v0.3.x+
                           |
                   cdb_context Contract
                           |
                  Agent Brain Protocol
                           |
         shared MCP transport (stdio + Streamable HTTP)
         agent-brain-mcp / agent-brain-mcp-http
                           |
     +----------+----------+----------+----------+
     |          |          |          |          |
 Claude Code  Cursor   OpenCode   ChatGPT
   adapter    adapter   adapter   remote plugin
```

Host adapters own packaging, installation/registration, transport binding, discovery, and minimal usage guidance. They do **not** own context/retrieval/required-reads/evidence/source-priority/trust/CDB business logic.

## Shared primitives

| Primitive | Location |
|---|---|
| MCP stdio entrypoint | `agent-brain-mcp` (fallback: `python -m agent_brain.mcp`) |
| MCP Streamable HTTP | `agent-brain-mcp-http` → `/mcp` (fallback: `python -m agent_brain.mcp.http`) |
| Canonical usage skill | `hosts/shared/skills/agent-brain-cdb-context/SKILL.md` |
| Capability contract | `docs/capabilities/CDB_CONTEXT_CONTRACT.md` |
| Shared contract suite | `tests/capabilities/test_host_contract_suite.py` |

Distributed skill copies under each host package must byte-match the canonical skill (enforced by tests).

## Host packages

- [Claude Code](claude-code/) — plugin + marketplace catalog + `.mcp.json`
- [Cursor](cursor/) — Agent Plugins (`plugin.json` + `mcp.json` + skill)
- [OpenCode](opencode/) — skill + MCP config example (no JS plugin)
- [ChatGPT](chatgpt/) — Agent Plugins package + remote MCP / Secure MCP Tunnel docs

## Install docs

See [docs/hosts/](../docs/hosts/README.md).
