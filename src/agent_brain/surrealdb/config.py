"""SurrealDB connection settings for the native read runtime (#10 / #38).

These settings capture endpoint and namespace/database mapping without importing
any SurrealDB SDK types. Defaults mirror Claire config evidence; DB-backed
existence of those names must still be verified at runtime (#38 baseline).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SurrealDbReadSettings:
    """Read-only connection parameters for Surreal HTTP access."""

    endpoint: str = "http://127.0.0.1:8010"
    namespace: str = "cdb_context_local"
    database: str = "cdb_context_intel"
    timeout_seconds: float = 2.0
    # Expected server major from #38 scratch evidence when digest-pinned locally.
    expected_server_version_prefix: str | None = "surrealdb-3.0"

    def __post_init__(self) -> None:
        endpoint = self.endpoint.strip().rstrip("/")
        if not endpoint:
            raise ValueError("endpoint must not be blank")
        if not endpoint.startswith(("http://", "https://")):
            raise ValueError("endpoint must be an http(s) URL")
        object.__setattr__(self, "endpoint", endpoint)
        ns = self.namespace.strip()
        db = self.database.strip()
        if not ns:
            raise ValueError("namespace must not be blank")
        if not db:
            raise ValueError("database must not be blank")
        object.__setattr__(self, "namespace", ns)
        object.__setattr__(self, "database", db)
        if isinstance(self.timeout_seconds, bool) or not isinstance(
            self.timeout_seconds, (int, float)
        ):
            raise TypeError("timeout_seconds must be a number")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        object.__setattr__(self, "timeout_seconds", float(self.timeout_seconds))
        prefix = self.expected_server_version_prefix
        if prefix is not None:
            normalized = prefix.strip()
            if not normalized:
                raise ValueError("expected_server_version_prefix must not be blank")
            object.__setattr__(self, "expected_server_version_prefix", normalized)
