from __future__ import annotations

from agent_brain.connectors import (
    ForbiddenRule,
    IngestionPolicy,
    RepositoryIngestionResult,
    RepositoryInventorySpec,
    build_repository_index,
    build_repository_inventory,
    normalize_ledger_events,
    scan_repository,
)


def test_slice_five_public_surface_exports_stable_entry_points() -> None:
    assert IngestionPolicy.__module__ == "agent_brain.connectors.ingestion"
    assert ForbiddenRule.__module__ == "agent_brain.connectors.ingestion"
    assert RepositoryIngestionResult.__module__ == "agent_brain.connectors.ingestion"
    assert RepositoryInventorySpec.__module__ == "agent_brain.connectors.inventory"
    assert callable(scan_repository)
    assert callable(build_repository_index)
    assert callable(build_repository_inventory)
    assert callable(normalize_ledger_events)
