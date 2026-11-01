# Install — ChatGPT (Agent Brain / `cdb_context`)

Parent: [#73](https://github.com/jannekbuengener/agent-brain/issues/73)  
Contract: [CDB_CONTEXT_CONTRACT.md](../capabilities/CDB_CONTEXT_CONTRACT.md)

## Prerequisites

1. `python -m pip install "agent-brain==0.3.3"` (exact pin; no `main` / `latest`).
2. ChatGPT account/workspace permission to **Add custom MCP server**.
3. For private/local servers: Platform access to create a **Secure MCP Tunnel** and run `tunnel-client` ([OpenAI Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)).

## Auth classification

`PUBLIC_READ_ONLY` — no user-scoped private data plane in Goal 3. Use **No authentication**. Do not commit tokens.

## Path A — Secure MCP Tunnel (preferred)

1. Start local MCP, either:
   - stdio: keep `agent-brain-mcp` available on PATH, or
   - HTTP: `agent-brain-mcp-http --host 127.0.0.1 --port 8787`
2. Create/manage a tunnel in Platform tunnel settings; associate the ChatGPT workspace.
3. Run `tunnel-client` with either `--mcp-command agent-brain-mcp` or `--mcp-server-url http://127.0.0.1:8787/mcp`.
4. Keep `tunnel-client` healthy (`/healthz`, `/readyz`, `/ui`).
5. ChatGPT → Plugins → **+** → **Add custom MCP server**:
   - Name: `Agent Brain`
   - Connection: **Tunnel** → select `tunnel_id`
   - Authentication: **No authentication**
   - Acknowledge risk → **Create as a plugin**
6. Install the plugin → open **Work** chat → type `@` → select Agent Brain.

## Path B — Stable HTTPS `/mcp` (when required)

1. Deploy `agent-brain-mcp-http` behind HTTPS with endpoint path `/mcp` (or current official MCP path).
2. Validate with MCP Inspector (Streamable HTTP) before ChatGPT.
3. ChatGPT → Add custom MCP server → paste `https://<host>/mcp` → No authentication → Create as plugin → install → `@` invoke.

Do **not** treat a temporary public HTTPS forwarder as production/public-submission evidence.

## MCP Inspector gate (before ChatGPT)

```bash
agent-brain-mcp-http --host 127.0.0.1 --port 8787
npx @modelcontextprotocol/inspector@latest
```

Inspector → Streamable HTTP → `http://127.0.0.1:8787/mcp`. Confirm:

- initialize
- exactly five tools with annotations
- health / briefing / search / required_reads / evidence
- invalid input, invalid scope, unavailable, contract mismatch, write denied

## Tool refresh / snapshot

After tool schema or annotation changes: restart/redeploy MCP → open the ChatGPT connection → **Refresh** → start a **new** conversation. Do not assume an old ChatGPT tool snapshot is current.

## Upgrade

1. Note current pin `agent-brain==X.Y.Z`.
2. Install target pin.
3. Restart local MCP / redeploy remote `/mcp`.
4. Restart `tunnel-client` if used.
5. ChatGPT connection → Refresh tools.
6. Smoke: health → briefing → search → required_reads → evidence.

## Rollback

1. Reinstall previous exact pin.
2. Restart MCP (+ tunnel-client if used).
3. Refresh ChatGPT tools.
4. Smoke health + one `cdb_context` call.

Forbidden: source-tree revert as rollback; unversioned `main` pins; absolute user paths.

## Out of scope (Goal 3)

Public plugin directory submission, custom UI, monetization, MCP Events, company-knowledge `search`/`fetch` shims.
