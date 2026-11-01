# OpenCode — Agent Brain adapter

Skills + local MCP registration. No OpenCode JS/TS plugin — Skill + MCP is sufficient.

## Prerequisites

1. `python -m pip install "agent-brain==0.3.2"`
2. OpenCode CLI available (`opencode`)

## Install skill

Copy or link the skill into an OpenCode skill search path, for example:

```text
~/.config/opencode/skills/agent-brain-cdb-context/SKILL.md
```

or project-local:

```text
.opencode/skills/agent-brain-cdb-context/SKILL.md
```

Source of truth remains `hosts/shared/skills/agent-brain-cdb-context/SKILL.md`.

## Register MCP

Merge `opencode.agent-brain.mcp.example.json` into your OpenCode config (`opencode.json` / `opencode.jsonc`):

```json
{
  "mcp": {
    "agent-brain": {
      "type": "local",
      "command": ["agent-brain-mcp"],
      "enabled": true
    }
  }
}
```

Verify:

```bash
opencode mcp list
```

## Upgrade / rollback

Reinstall the exact previous/next `agent-brain==X.Y.Z` pin, restart OpenCode, re-check MCP list + health. No source-checkout revert as the rollback mechanism.

## What this adapter must not contain

No OpenCode plugin JavaScript, no host-local capability logic, no Claire runtime.
