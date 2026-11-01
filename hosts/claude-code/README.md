# Claude Code — Agent Brain adapter

Thin Claude Code plugin. MCP tools come from the shared `python -m agent_brain.mcp` entrypoint. Skill body is synced from `hosts/shared/skills/`.

## Prerequisites

1. Install a pinned Agent Brain release: `python -m pip install "agent-brain==0.3.2"`
2. Ensure `agent-brain-mcp` is on PATH (from that install)
3. Claude Code CLI available (`claude`)

## Install (local marketplace)

From this repository (or a checkout that contains `hosts/claude-code`):

```bash
claude plugin marketplace add ./hosts/claude-code
claude plugin install agent-brain@agent-brain-local
```

Validate before install:

```bash
claude plugin validate ./hosts/claude-code/plugins/agent-brain
claude plugin validate ./hosts/claude-code
```

Developer load without marketplace:

```bash
claude --plugin-dir ./hosts/claude-code/plugins/agent-brain
```

## Upgrade / rollback

Upgrade/rollback the **Python package pin**, then reload plugins:

```bash
python -m pip install "agent-brain==<target>"
# then restart Claude Code / reload plugins
```

Do not pin `main` or absolute workstation paths.

## What this adapter must not contain

No host-local `cdb_context` implementation, ranking, evidence logic, or Claire runtime.
