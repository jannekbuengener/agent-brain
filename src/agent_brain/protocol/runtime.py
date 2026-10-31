"""Injectable runtime bindings for the public protocol surface.

Defaults keep Agent Brain installable and usable without MCP, SurrealDB, or a
developer workspace. Optional backends are reported honestly as unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_brain.memory.ports import KnowledgeStore, MemoryStore
from agent_brain.memory.unavailable import UnavailableKnowledgeStore, UnavailableMemoryStore
from agent_brain.surrealdb.config import SurrealDbReadSettings


@dataclass(slots=True)
class ProtocolRuntime:
    """Transport-agnostic dependency bag for protocol operations.

    ``memory_store`` / ``knowledge_store`` default to explicit unavailable
    adapters so missing backends cannot be mistaken for empty success.
    """

    memory_store: MemoryStore = field(default_factory=UnavailableMemoryStore)
    knowledge_store: KnowledgeStore = field(default_factory=UnavailableKnowledgeStore)
    surreal_settings: SurrealDbReadSettings | None = None
    surreal_probe_enabled: bool = False

    @property
    def memory_backend_configured(self) -> bool:
        # Exact default marker only. Subclasses or alternate unavailable adapters
        # count as configured backends so BACKEND_UNAVAILABLE can surface.
        return type(self.memory_store) is not UnavailableMemoryStore

    @property
    def surreal_configured(self) -> bool:
        return self.surreal_settings is not None


def default_runtime() -> ProtocolRuntime:
    """Claire-/MCP-/workspace-free default runtime for installed consumers."""
    return ProtocolRuntime()


__all__ = [
    "ProtocolRuntime",
    "default_runtime",
]
