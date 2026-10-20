"""Read-only, deterministic repository-ingestion APIs.

The package exposes the stable Slice-5 surface only. It neither persists data
nor opens network or database connections.
"""

from agent_brain.connectors.indexer import (
    build_repository_index,
    extract_config_records,
    extract_markdown_records,
    extract_python_records,
)
from agent_brain.connectors.ingestion import (
    ForbiddenRule,
    IngestionFinding,
    IngestionPolicy,
    RepositoryIngestionResult,
    SensitivityRule,
    build_ingestion_fingerprint,
)
from agent_brain.connectors.inventory import (
    RepositoryInventoryEntry,
    RepositoryInventoryReport,
    RepositoryInventorySpec,
    build_repository_inventory,
    read_git_origin,
)
from agent_brain.connectors.ledger import LedgerIntegrityError, normalize_ledger_events
from agent_brain.connectors.scanner import (
    ScannedSource,
    ScanResult,
    classify_file_type,
    scan_repository,
)

__all__ = [
    "ForbiddenRule",
    "IngestionFinding",
    "IngestionPolicy",
    "LedgerIntegrityError",
    "RepositoryIngestionResult",
    "RepositoryInventoryEntry",
    "RepositoryInventoryReport",
    "RepositoryInventorySpec",
    "ScanResult",
    "ScannedSource",
    "SensitivityRule",
    "build_ingestion_fingerprint",
    "build_repository_index",
    "build_repository_inventory",
    "classify_file_type",
    "extract_config_records",
    "extract_markdown_records",
    "extract_python_records",
    "normalize_ledger_events",
    "read_git_origin",
    "scan_repository",
]
