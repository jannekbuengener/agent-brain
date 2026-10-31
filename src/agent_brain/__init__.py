"""Agent Brain — generic context, evidence, memory, retrieval, and knowledge core.

The installable package version is the single distribution source of truth (#17).
Runtime consumers should read ``agent_brain.__version__`` or
``importlib.metadata.version("agent-brain")``.
"""

from __future__ import annotations

from importlib import metadata

try:
    __version__ = metadata.version("agent-brain")
except metadata.PackageNotFoundError:  # pragma: no cover - only when not installed
    __version__ = "0.0.0"

__all__ = [
    "__version__",
]
