"""``python -m agent_brain.mcp`` — shared stdio MCP entrypoint."""

from __future__ import annotations

from agent_brain.mcp.server import main

raise SystemExit(main())
