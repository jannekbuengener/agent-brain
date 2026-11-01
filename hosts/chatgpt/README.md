# ChatGPT — Agent Brain Plugin

Parent: [#73](https://github.com/jannekbuengener/agent-brain/issues/73)  
Capability contract: [CDB_CONTEXT_CONTRACT.md](../../docs/capabilities/CDB_CONTEXT_CONTRACT.md)

## Architecture

```text
ChatGPT
  → Agent Brain Plugin (this package)
  → Secure MCP Tunnel | HTTPS /mcp
  → shared Agent Brain MCP transport
  → CapabilityGateway
  → cdb_context
  → agent_brain.protocol
  → Agent Brain Core
```

No ChatGPT-specific context/retrieval/evidence fork. Tool-only; no custom UI.

## Auth model

`PUBLIC_READ_ONLY` — no OAuth invented for Goal 3. Manifest declares `auth.type: none`.

## Preferred connection

1. Install pinned package: `python -m pip install "agent-brain==0.3.3"`
2. Run local MCP (stdio **or** Streamable HTTP):
   - `agent-brain-mcp` (stdio; Secure MCP Tunnel `--mcp-command`)
   - `agent-brain-mcp-http --host 127.0.0.1 --port 8787` → `http://127.0.0.1:8787/mcp`
3. Prefer **Secure MCP Tunnel** (`tunnel-client`) for private/local development.
4. In ChatGPT Plugins → Add custom MCP server → Tunnel (or HTTPS `/mcp` URL).
5. Create as plugin → install → Work chat → `@Agent Brain`.

Public plugin-directory submission is **out of scope** for Goal 3.

## Package layout

- `agent-brain/plugin.json` — identity
- `agent-brain/mcp.json` — remote MCP declaration (placeholder URL; no secrets)
- `agent-brain/skills/agent-brain-cdb-context/` — shared usage skill (byte-identical to canonical)

## Docs

See [docs/hosts/INSTALL_CHATGPT.md](../../docs/hosts/INSTALL_CHATGPT.md).
