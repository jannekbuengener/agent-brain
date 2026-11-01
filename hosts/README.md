# Host Surfaces — Agent Brain / `cdb_context`

Parent: [#73](https://github.com/jannekbuengener/agent-brain/issues/73)  
Delivery: Goal 2 — Local Host Surfaces (Claude Code, Cursor, OpenCode)

## Architecture

```text
                    Agent Brain v0.3.x+
                           |
                   cdb_context Contract
                           |
                  Agent Brain Protocol
                           |
              host-neutral MCP/tool layer
              (python -m agent_brain.mcp)
                           |
        +------------------+------------------+
        |                  |                  |
   Claude Code          Cursor            OpenCode
     adapter            adapter            adapter
```

Host adapters own packaging, installation/registration, transport binding, discovery, and minimal usage guidance. They do **not** own context/retrieval/required-reads/evidence/source-priority/trust/CDB business logic.

## Shared primitives

| Primitive | Location |
|---|---|
| MCP stdio entrypoint | `agent-brain-mcp` (fallback: `python -m agent_brain.mcp`) |
| Canonical usage skill | `hosts/shared/skills/agent-brain-cdb-context/SKILL.md` |
| Capability contract | `docs/capabilities/CDB_CONTEXT_CONTRACT.md` |
| Shared contract suite | `tests/capabilities/test_host_contract_suite.py` |

Distributed skill copies under each host package must byte-match the canonical skill (enforced by tests).

## Host packages

- [Claude Code](claude-code/) — plugin + marketplace catalog + `.mcp.json`
- [Cursor](cursor/) — Agent Plugins (`plugin.json` + `mcp.json` + skill)
- [OpenCode](opencode/) — skill + MCP config example (no JS plugin)

## Install docs

See [docs/hosts/](../docs/hosts/README.md).

## ChatGPT

Out of scope for Goal 2. Tracked under the same parent #73 for a later delivery goal.
