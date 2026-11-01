# Multi-Surface Host Documentation

**Parent:** [#73](https://github.com/jannekbuengener/agent-brain/issues/73)  
**Capability contract (single source):** [CDB_CONTEXT_CONTRACT.md](../capabilities/CDB_CONTEXT_CONTRACT.md)

## Architecture

Siehe [hosts/README.md](../../hosts/README.md). Host-Dokumente **duplizieren** den Capability Contract nicht — sie verlinken ihn.

## Install

- [Claude Code](INSTALL_CLAUDE_CODE.md)
- [Cursor](INSTALL_CURSOR.md)
- [OpenCode](INSTALL_OPENCODE.md)
- [ChatGPT](INSTALL_CHATGPT.md)

## Operations

- [Finale #73-Abnahme und Nachweislücken](GOAL4_ACCEPTANCE.md)
- [Upgrade / Rollback](UPGRADE_ROLLBACK.md)
- [Troubleshooting](TROUBLESHOOTING.md)

## Contract / Version relationship

| Layer | Source of truth |
|---|---|
| Package version | `pyproject.toml` / `agent_brain.__version__` / tag `vX.Y.Z` (#17) |
| Capability contract schema | `agent-brain-cdb-context-capability/v1` |
| MCP stdio schema | `agent-brain-mcp-stdio/v1` |
| MCP Streamable HTTP schema | `agent-brain-mcp-streamable-http/v1` |
| Protocol schema | `agent-brain-protocol/v1` (#12) |

Hosts must pin an exact Agent Brain version. Unversioned `main` pins and absolute user paths are forbidden.

## ChatGPT notes

Preferred private path: **Secure MCP Tunnel** to local `agent-brain-mcp` or `agent-brain-mcp-http`.  
Public directory submission remains out of scope until an explicit owner decision under #73.
