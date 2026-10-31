"""Standalone Agent Brain CLI transport (#12).

The CLI is a thin adapter over ``agent_brain.protocol``. It does not embed
domain logic, Claire business rules, private MCP, or write surfaces.
"""

from __future__ import annotations

from agent_brain.cli.main import build_parser, main

__all__ = [
    "build_parser",
    "main",
]
