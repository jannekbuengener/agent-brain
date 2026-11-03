"""Append-only, repository-scoped cross-agent handoff journal backed by SurrealDB 3.

This is a narrow, explicit write capability. It does not extend the read-only
MemoryStore port and does not grant arbitrary memory or SurrealQL writes.
A single local trusted operator controls the root credential in this first slice.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agent_brain.surrealdb.config import SurrealDbReadSettings
from agent_brain.surrealdb.http import (
    SurrealHttpProbeResult,
    parse_json_body,
    post_sql,
    probe_version,
)

_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")
_AGENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_STATES = frozenset({"in_progress", "blocked", "completed"})
_TABLE = "agent_handoff"
_SCHEMA = (
    f"DEFINE TABLE IF NOT EXISTS {_TABLE} SCHEMAFULL;",
    f"DEFINE FIELD IF NOT EXISTS event_key ON {_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS repository_ref ON {_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS agent_id ON {_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS task_ref ON {_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS status ON {_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS summary ON {_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS next_step ON {_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS source_ref ON {_TABLE} TYPE string;",
    f"DEFINE FIELD IF NOT EXISTS created_at ON {_TABLE} TYPE string;",
    f"DEFINE INDEX IF NOT EXISTS handoff_event_key_unique ON {_TABLE} FIELDS event_key UNIQUE;",
    f"DEFINE INDEX IF NOT EXISTS handoff_repo_task ON {_TABLE} FIELDS repository_ref, task_ref;",
    f"DEFINE INDEX IF NOT EXISTS handoff_repo_created ON {_TABLE} FIELDS repository_ref, created_at;",
)


class HandoffUnavailable(RuntimeError):
    """Fail-closed backend / authorization / schema failure."""


class HandoffConflict(ValueError):
    """An idempotency key was already used for different content."""


def _require_text(value: object, field: str, *, max_len: int) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be text")
    value = value.strip()
    if not value or len(value) > max_len:
        raise ValueError(f"{field} must be between 1 and {max_len} characters")
    return value


def _sql_string(value: str) -> str:
    """JSON strings are valid SurrealQL string literals, never raw query fragments."""
    return json.dumps(value, ensure_ascii=True)


def load_local_authorization(secret_dir: str | Path | None = None) -> str:
    """Read SURREAL_USER / SURREAL_PASS without placing values in logs or repo."""
    raw = secret_dir or os.environ.get("AGENT_BRAIN_SECRETS_PATH")
    if not raw:
        raise HandoffUnavailable("AGENT_BRAIN_SECRETS_PATH is not configured")
    path = Path(raw) / "SURREALDB_ENV"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise HandoffUnavailable("Agent Brain SurrealDB credential file unavailable") from exc
    fields: dict[str, str] = {}
    for line in lines:
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        if key.strip() in {"SURREAL_USER", "SURREAL_PASS"}:
            fields[key.strip()] = value.strip()
    if not fields.get("SURREAL_USER") or not fields.get("SURREAL_PASS"):
        raise HandoffUnavailable("Agent Brain SurrealDB credentials incomplete")
    pair = (fields["SURREAL_USER"] + ":" + fields["SURREAL_PASS"]).encode("utf-8")
    return "Basic " + base64.b64encode(pair).decode("ascii")


@dataclass(frozen=True, slots=True)
class HandoffEvent:
    event_key: str
    repository_ref: str
    agent_id: str
    task_ref: str
    status: str
    summary: str
    next_step: str
    source_ref: str
    created_at: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _records(result: SurrealHttpProbeResult) -> list[Mapping[str, Any]]:
    if not result.ok:
        raise HandoffUnavailable("SurrealDB endpoint/auth unavailable")
    payload = parse_json_body(result.body_text)
    if not isinstance(payload, list):
        raise HandoffUnavailable("SurrealDB response format invalid")
    rows: list[Mapping[str, Any]] = []
    for statement in payload:
        if not isinstance(statement, Mapping) or statement.get("status") != "OK":
            raise HandoffUnavailable("SurrealDB statement rejected")
        data = statement.get("result")
        if isinstance(data, list):
            rows.extend(row for row in data if isinstance(row, Mapping))
        elif isinstance(data, Mapping):
            rows.append(data)
    return rows


def _event(row: Mapping[str, Any]) -> HandoffEvent:
    try:
        return HandoffEvent(**{key: str(row[key]) for key in HandoffEvent.__dataclass_fields__})
    except (KeyError, TypeError, ValueError) as exc:
        raise HandoffUnavailable("Stored handoff record missing required fields") from exc


class SurrealHandoffJournal:
    """Trusted local writer/reader with exact repository filtering and idempotency."""

    def __init__(
        self,
        settings: SurrealDbReadSettings | None = None,
        *,
        authorization: str | None = None,
        sql_executor: Callable[..., SurrealHttpProbeResult] = post_sql,
        version_prober: Callable[..., SurrealHttpProbeResult] = probe_version,
        initialize: bool = True,
    ) -> None:
        self.settings = settings or SurrealDbReadSettings(
            endpoint="http://127.0.0.1:8012",
            namespace="agent_brain",
            database="shared_memory",
        )
        self._authorization = authorization
        self._execute_sql = sql_executor
        self._version_probe = version_prober
        if initialize:
            self.initialize()

    def _execute(
        self, statement: str, *, ns: str | None = None, db: str | None = None
    ) -> list[Mapping[str, Any]]:
        return _records(
            self._execute_sql(
                self.settings.endpoint,
                statement,
                namespace=self.settings.namespace if ns is None else ns,
                database=self.settings.database if db is None else db,
                timeout_seconds=self.settings.timeout_seconds,
                authorization=self._authorization,
            )
        )

    def initialize(self) -> None:
        version = self._version_probe(
            self.settings.endpoint,
            timeout_seconds=self.settings.timeout_seconds,
        )
        if not version.ok or not version.version_text:
            raise HandoffUnavailable("SurrealDB version endpoint unavailable")
        expected = self.settings.expected_server_version_prefix
        if expected and not version.version_text.startswith(expected):
            raise HandoffUnavailable("SurrealDB server version unsupported")
        # Identifiers are structural settings. Never interpolate arbitrary unvalidated names.
        for value in (self.settings.namespace, self.settings.database):
            if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", value):
                raise ValueError("Surreal namespace/database must be safe lowercase identifiers")
        self._execute(f"DEFINE NAMESPACE IF NOT EXISTS {self.settings.namespace};", ns="", db="")
        self._execute(f"DEFINE DATABASE IF NOT EXISTS {self.settings.database};", db="")
        for statement in _SCHEMA:
            self._execute(statement)
        self._execute(f"SELECT event_key FROM {_TABLE} LIMIT 1;")

    @staticmethod
    def _validate_input(
        *,
        repository_ref: str,
        agent_id: str,
        task_ref: str,
        status: str,
        summary: str,
        next_step: str,
        source_ref: str,
        idempotency_key: str,
    ) -> dict[str, str]:
        repo = _require_text(repository_ref, "repository_ref", max_len=150)
        agent = _require_text(agent_id, "agent_id", max_len=64)
        if not _REPOSITORY_RE.fullmatch(repo):
            raise ValueError("repository_ref must be owner/repo")
        if not _AGENT_RE.fullmatch(agent):
            raise ValueError("agent_id contains invalid characters")
        if status not in _STATES:
            raise ValueError("status must be in_progress, blocked or completed")
        return {
            "repository_ref": repo,
            "agent_id": agent,
            "task_ref": _require_text(task_ref, "task_ref", max_len=256),
            "status": status,
            "summary": _require_text(summary, "summary", max_len=4000),
            "next_step": _require_text(next_step, "next_step", max_len=2000),
            "source_ref": _require_text(source_ref, "source_ref", max_len=512),
            "idempotency_key": _require_text(idempotency_key, "idempotency_key", max_len=256),
        }

    def append(
        self,
        *,
        repository_ref: str,
        agent_id: str,
        task_ref: str,
        status: str,
        summary: str,
        next_step: str,
        source_ref: str,
        idempotency_key: str,
    ) -> HandoffEvent:
        data = self._validate_input(
            repository_ref=repository_ref,
            agent_id=agent_id,
            task_ref=task_ref,
            status=status,
            summary=summary,
            next_step=next_step,
            source_ref=source_ref,
            idempotency_key=idempotency_key,
        )
        key = hashlib.sha256(
            (data["repository_ref"] + "\x00" + data.pop("idempotency_key")).encode("utf-8")
        ).hexdigest()
        existing = self._find_key(key)
        if existing is not None:
            self._check_retry(existing, data)
            return existing
        event = HandoffEvent(
            event_key=key,
            created_at=datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z"),
            **data,
        )
        body = ", ".join(
            f"{name}: {_sql_string(str(value))}" for name, value in event.to_dict().items()
        )
        try:
            self._execute(f"CREATE {_TABLE} CONTENT {{ {body} }};")
        except HandoffUnavailable:
            # A concurrent retry may have won the UNIQUE race. Fail closed on
            # any other error and never misclassify an unavailable backend as success.
            winner = self._find_key(key)
            if winner is None:
                raise
            self._check_retry(winner, data)
            return winner
        saved = self._find_key(key)
        if saved is None:
            raise HandoffUnavailable("SurrealDB write not visible after insert")
        self._check_retry(saved, data)
        return saved

    @staticmethod
    def _check_retry(existing: HandoffEvent, data: Mapping[str, str]) -> None:
        for name, value in data.items():
            if getattr(existing, name) != value:
                raise HandoffConflict("idempotency key already belongs to a different event")

    def _find_key(self, key: str) -> HandoffEvent | None:
        rows = self._execute(
            f"SELECT * FROM {_TABLE} WHERE event_key = {_sql_string(key)} LIMIT 2;"
        )
        if len(rows) > 1:
            raise HandoffUnavailable("duplicate persistent memory event_key")
        return _event(rows[0]) if rows else None

    def recall(
        self,
        *,
        repository_ref: str,
        task_ref: str | None = None,
        limit: int = 20,
    ) -> list[HandoffEvent]:
        repo = _require_text(repository_ref, "repository_ref", max_len=150)
        if not _REPOSITORY_RE.fullmatch(repo):
            raise ValueError("repository_ref must be owner/repo")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("limit must be an integer from 1 to 100")
        info = self._execute("INFO FOR DB;")
        if (
            len(info) != 1
            or not isinstance(info[0].get("tables"), Mapping)
            or _TABLE not in info[0]["tables"]
        ):
            raise HandoffUnavailable("Shared handoff schema unavailable")
        filter_clause = f"repository_ref = {_sql_string(repo)}"
        if task_ref is not None:
            target = _require_text(task_ref, "task_ref", max_len=256)
            filter_clause += f" AND task_ref = {_sql_string(target)}"
        rows = self._execute(
            f"SELECT * FROM {_TABLE} WHERE {filter_clause} ORDER BY created_at DESC LIMIT {limit};"
        )
        events = [_event(row) for row in rows]
        if any(
            item.repository_ref != repo or (task_ref is not None and item.task_ref != task_ref)
            for item in events
        ):
            raise HandoffUnavailable("Repository isolation violated by returned result")
        return events
