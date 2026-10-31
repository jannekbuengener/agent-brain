"""Stdlib HTTP helpers for SurrealDB read probes (#10).

No SurrealDB SDK dependency. Failures surface as structured probe results so
callers can map them to StoreAvailability.UNAVAILABLE without inventing empty
state.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SurrealHttpProbeResult:
    """Outcome of a single HTTP probe against a Surreal endpoint."""

    ok: bool
    status_code: int | None = None
    body_text: str | None = None
    error: str | None = None

    @property
    def version_text(self) -> str | None:
        if not self.ok or self.body_text is None:
            return None
        return self.body_text.strip() or None


def probe_version(endpoint: str, *, timeout_seconds: float) -> SurrealHttpProbeResult:
    """GET ``/version``; used as the lightest DB-/endpoint-backed liveness check."""
    url = f"{endpoint.rstrip('/')}/version"
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
            return SurrealHttpProbeResult(
                ok=200 <= response.status < 300,
                status_code=response.status,
                body_text=body,
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else None
        return SurrealHttpProbeResult(
            ok=False,
            status_code=exc.code,
            body_text=body,
            error=f"http_error:{exc.code}",
        )
    except Exception as exc:  # noqa: BLE001 — boundary maps all transport failures
        return SurrealHttpProbeResult(ok=False, error=f"{type(exc).__name__}:{exc}")


def post_sql(
    endpoint: str,
    sql: str,
    *,
    namespace: str,
    database: str,
    timeout_seconds: float,
    authorization: str | None = None,
) -> SurrealHttpProbeResult:
    """POST plain-text SurrealQL to ``/sql`` with NS/DB headers."""
    url = f"{endpoint.rstrip('/')}/sql"
    headers = {
        "Accept": "application/json",
        "Content-Type": "text/plain",
    }
    if namespace:
        headers["surreal-ns"] = namespace
    if database:
        headers["surreal-db"] = database
    if authorization:
        headers["Authorization"] = authorization
    request = urllib.request.Request(
        url,
        data=sql.encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
            return SurrealHttpProbeResult(
                ok=200 <= response.status < 300,
                status_code=response.status,
                body_text=body,
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else None
        return SurrealHttpProbeResult(
            ok=False,
            status_code=exc.code,
            body_text=body,
            error=f"http_error:{exc.code}",
        )
    except Exception as exc:  # noqa: BLE001
        return SurrealHttpProbeResult(ok=False, error=f"{type(exc).__name__}:{exc}")


def parse_json_body(body_text: str | None) -> Any | None:
    if body_text is None:
        return None
    try:
        return json.loads(body_text)
    except json.JSONDecodeError:
        return None
