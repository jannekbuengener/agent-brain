# Cursor — Agent Brain adapter

Portable **Agent Plugins** package (skills + MCP). Prefer this over Cursor-only rules/agents/hooks unless a real need appears (YAGNI).

## Prerequisites

1. `python -m pip install "agent-brain==0.3.1"`
2. Cursor with Agent Plugins support

## Install / register

Point Cursor at the plugin directory:

```text
hosts/cursor/agent-brain/
```

Manifest: root `plugin.json` (Agent Plugins schema). MCP: root `mcp.json` launching `python -m agent_brain.mcp`.

Skill: `skills/agent-brain-cdb-context/SKILL.md` (synced from shared canonical skill).

## Upgrade / rollback

Change the installed Agent Brain pin (`agent-brain==X.Y.Z`), restart Cursor / reload plugins, confirm health + version match. No `latest`, no absolute user paths.

## What this adapter must not contain

No Cursor-specific context core, no rules/agents/hooks unless later justified, no Claire runtime.
