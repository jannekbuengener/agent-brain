"""Consumer AuthN/AuthZ for shared work handoffs (Meta-Goal #96 / G1).

Stores protected token hashes only. Plaintext consumer tokens are shown once at
enroll/rotate and never persisted. An append-only revoke denylist lives under
AGENT_BRAIN_SECRETS_PATH (outside the SurrealDB volume) so restoring an older
database/grant snapshot cannot unintentionally revive revoked credentials.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")
_CONSUMER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_TOKEN_PREFIX = "abh_"
_PEPPER_FILE = "HANDOFF_TOKEN_PEPPER"
_GRANTS_FILE = "handoff_grants.json"
_DENYLIST_FILE = "handoff_revoke_denylist.jsonl"
HANDOFF_AUTH_SCHEMA_VERSION = "handoff-auth/v1"


class HandoffOperation(StrEnum):
    APPEND = "append"
    RECALL = "recall"


class HandoffForbidden(PermissionError):
    """Authenticated identity missing, revoked, or lacking the requested grant."""


class HandoffAuthUnavailable(RuntimeError):
    """Fail-closed credential-store / pepper failure (not an empty grant)."""


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _secrets_dir(secret_dir: str | Path | None = None) -> Path:
    raw = secret_dir if secret_dir is not None else os.environ.get("AGENT_BRAIN_SECRETS_PATH")
    if not raw:
        raise HandoffAuthUnavailable("AGENT_BRAIN_SECRETS_PATH is not configured")
    path = Path(raw)
    if not path.is_dir():
        raise HandoffAuthUnavailable("Agent Brain secrets directory unavailable")
    return path


def load_or_create_pepper(secret_dir: str | Path | None = None) -> bytes:
    """Load HMAC pepper from secrets dir; create once if missing (operator host only)."""
    directory = _secrets_dir(secret_dir)
    path = directory / _PEPPER_FILE
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if len(value) < 32:
            raise HandoffAuthUnavailable("handoff token pepper is incomplete")
        return value.encode("utf-8")
    value = secrets.token_hex(32)
    path.write_text(value + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return value.encode("utf-8")


def mint_consumer_token() -> str:
    return _TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_consumer_token(token: str, *, pepper: bytes) -> str:
    if not isinstance(token, str) or not token.startswith(_TOKEN_PREFIX) or len(token) < 20:
        raise HandoffForbidden("consumer token rejected")
    digest = hmac.new(pepper, token.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest


@dataclass(frozen=True, slots=True)
class HandoffGrant:
    grant_id: str
    consumer_id: str
    repository_ref: str
    operations: frozenset[HandoffOperation]
    token_hash: str
    created_at: str
    status: str = "active"
    rotated_from: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "consumer_id": self.consumer_id,
            "repository_ref": self.repository_ref,
            "operations": sorted(op.value for op in self.operations),
            "created_at": self.created_at,
            "status": self.status,
            "rotated_from": self.rotated_from,
            # Never expose token_hash in ordinary operator listings.
        }


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Server-derived caller context. Payload agent_id is never an auth trust anchor."""

    consumer_id: str
    repository_ref: str
    grant_id: str
    operations: frozenset[HandoffOperation]
    token_hash_prefix: str


def _parse_operations(raw: Iterable[str] | Iterable[HandoffOperation]) -> frozenset[HandoffOperation]:
    ops: set[HandoffOperation] = set()
    for item in raw:
        ops.add(item if isinstance(item, HandoffOperation) else HandoffOperation(str(item)))
    if not ops:
        raise ValueError("operations must not be empty")
    return frozenset(ops)


class RevokeDenylist:
    """Append-only revoke log kept outside the SurrealDB data volume."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._memory: set[str] = set()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if isinstance(row, Mapping) and isinstance(row.get("token_hash"), str):
                    self._memory.add(row["token_hash"])

    def contains(self, token_hash: str) -> bool:
        return token_hash in self._memory

    def revoke(
        self,
        token_hash: str,
        *,
        grant_id: str,
        consumer_id: str,
        reason: str,
    ) -> None:
        if token_hash in self._memory:
            return
        record = {
            "token_hash": token_hash,
            "grant_id": grant_id,
            "consumer_id": consumer_id,
            "reason": reason,
            "revoked_at": _utc_now(),
            "schema": HANDOFF_AUTH_SCHEMA_VERSION,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")
        try:
            self.path.chmod(0o600)
        except OSError:
            pass
        self._memory.add(token_hash)


class HandoffCredentialStore:
    """Grant registry with hashed tokens + external revoke denylist."""

    def __init__(
        self,
        *,
        pepper: bytes,
        grants: dict[str, HandoffGrant] | None = None,
        denylist: RevokeDenylist | None = None,
        grants_path: Path | None = None,
    ) -> None:
        self._pepper = pepper
        self._grants_by_id: dict[str, HandoffGrant] = dict(grants or {})
        self._by_hash: dict[str, str] = {
            grant.token_hash: grant.grant_id
            for grant in self._grants_by_id.values()
            if grant.status == "active"
        }
        self._denylist = denylist
        self._grants_path = grants_path

    @classmethod
    def for_secrets_dir(cls, secret_dir: str | Path | None = None) -> HandoffCredentialStore:
        directory = _secrets_dir(secret_dir)
        pepper = load_or_create_pepper(directory)
        grants_path = directory / _GRANTS_FILE
        denylist = RevokeDenylist(directory / _DENYLIST_FILE)
        grants: dict[str, HandoffGrant] = {}
        if grants_path.exists():
            payload = json.loads(grants_path.read_text(encoding="utf-8"))
            if not isinstance(payload, Mapping) or payload.get("schema") != HANDOFF_AUTH_SCHEMA_VERSION:
                raise HandoffAuthUnavailable("handoff grant registry schema mismatch")
            for row in payload.get("grants", []):
                grant = _grant_from_row(row)
                grants[grant.grant_id] = grant
        return cls(pepper=pepper, grants=grants, denylist=denylist, grants_path=grants_path)

    def export_grants_snapshot(self) -> dict[str, Any]:
        """Serializable grant registry (hashes only) for backup/restore drills."""
        return {
            "schema": HANDOFF_AUTH_SCHEMA_VERSION,
            "grants": [
                {
                    **{k: v for k, v in asdict(grant).items() if k != "operations"},
                    "operations": sorted(op.value for op in grant.operations),
                }
                for grant in self._grants_by_id.values()
            ],
        }

    def restore_grants_snapshot(self, snapshot: Mapping[str, Any]) -> None:
        """Restore grant rows from an older backup without clearing the denylist."""
        if snapshot.get("schema") != HANDOFF_AUTH_SCHEMA_VERSION:
            raise HandoffAuthUnavailable("handoff grant snapshot schema mismatch")
        grants: dict[str, HandoffGrant] = {}
        by_hash: dict[str, str] = {}
        for row in snapshot.get("grants", []):
            grant = _grant_from_row(row)
            grants[grant.grant_id] = grant
            if grant.status == "active":
                by_hash[grant.token_hash] = grant.grant_id
        self._grants_by_id = grants
        self._by_hash = by_hash
        self._persist()

    def enroll(
        self,
        *,
        consumer_id: str,
        repository_ref: str,
        operations: Iterable[str] | Iterable[HandoffOperation],
    ) -> tuple[HandoffGrant, str]:
        consumer = _require_consumer(consumer_id)
        repo = _require_repo(repository_ref)
        ops = _parse_operations(operations)
        token = mint_consumer_token()
        token_hash = hash_consumer_token(token, pepper=self._pepper)
        grant = HandoffGrant(
            grant_id="grant_" + secrets.token_hex(8),
            consumer_id=consumer,
            repository_ref=repo,
            operations=ops,
            token_hash=token_hash,
            created_at=_utc_now(),
            status="active",
        )
        self._grants_by_id[grant.grant_id] = grant
        self._by_hash[token_hash] = grant.grant_id
        self._persist()
        return grant, token

    def rotate(self, grant_id: str) -> tuple[HandoffGrant, str]:
        existing = self._require_grant(grant_id)
        if existing.status != "active":
            raise HandoffForbidden("grant is not active")
        self.revoke(grant_id, reason="rotated")
        token = mint_consumer_token()
        token_hash = hash_consumer_token(token, pepper=self._pepper)
        grant = HandoffGrant(
            grant_id="grant_" + secrets.token_hex(8),
            consumer_id=existing.consumer_id,
            repository_ref=existing.repository_ref,
            operations=existing.operations,
            token_hash=token_hash,
            created_at=_utc_now(),
            status="active",
            rotated_from=existing.grant_id,
        )
        self._grants_by_id[grant.grant_id] = grant
        self._by_hash[token_hash] = grant.grant_id
        self._persist()
        return grant, token

    def revoke(self, grant_id: str, *, reason: str = "revoked") -> HandoffGrant:
        grant = self._require_grant(grant_id)
        if self._denylist is None:
            raise HandoffAuthUnavailable("revoke denylist is not configured")
        self._denylist.revoke(
            grant.token_hash,
            grant_id=grant.grant_id,
            consumer_id=grant.consumer_id,
            reason=reason,
        )
        revoked = HandoffGrant(
            grant_id=grant.grant_id,
            consumer_id=grant.consumer_id,
            repository_ref=grant.repository_ref,
            operations=grant.operations,
            token_hash=grant.token_hash,
            created_at=grant.created_at,
            status="revoked",
            rotated_from=grant.rotated_from,
        )
        self._grants_by_id[grant.grant_id] = revoked
        self._by_hash.pop(grant.token_hash, None)
        self._persist()
        return revoked

    def authenticate(
        self,
        token: str,
        *,
        repository_ref: str,
        operation: HandoffOperation | str,
    ) -> RequestContext:
        op = operation if isinstance(operation, HandoffOperation) else HandoffOperation(operation)
        repo = _require_repo(repository_ref)
        token_hash = hash_consumer_token(token, pepper=self._pepper)
        if self._denylist is not None and self._denylist.contains(token_hash):
            raise HandoffForbidden("consumer credential revoked")
        grant_id = self._by_hash.get(token_hash)
        if grant_id is None:
            raise HandoffForbidden("consumer credential rejected")
        grant = self._grants_by_id[grant_id]
        if grant.status != "active":
            raise HandoffForbidden("consumer credential revoked")
        if grant.repository_ref != repo:
            raise HandoffForbidden("repository grant denied")
        if op not in grant.operations:
            raise HandoffForbidden("operation grant denied")
        return RequestContext(
            consumer_id=grant.consumer_id,
            repository_ref=grant.repository_ref,
            grant_id=grant.grant_id,
            operations=grant.operations,
            token_hash_prefix=token_hash[:12],
        )

    def list_grants(self) -> list[HandoffGrant]:
        return sorted(self._grants_by_id.values(), key=lambda g: g.created_at)

    def _require_grant(self, grant_id: str) -> HandoffGrant:
        grant = self._grants_by_id.get(grant_id)
        if grant is None:
            raise HandoffForbidden("unknown grant_id")
        return grant

    def _persist(self) -> None:
        if self._grants_path is None:
            return
        payload = self.export_grants_snapshot()
        self._grants_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )
        try:
            self._grants_path.chmod(0o600)
        except OSError:
            pass


def _grant_from_row(row: Mapping[str, Any]) -> HandoffGrant:
    return HandoffGrant(
        grant_id=str(row["grant_id"]),
        consumer_id=str(row["consumer_id"]),
        repository_ref=str(row["repository_ref"]),
        operations=_parse_operations(row["operations"]),
        token_hash=str(row["token_hash"]),
        created_at=str(row["created_at"]),
        status=str(row.get("status", "active")),
        rotated_from=None if row.get("rotated_from") is None else str(row["rotated_from"]),
    )


def _require_consumer(value: str) -> str:
    text = value.strip()
    if not _CONSUMER_RE.fullmatch(text):
        raise ValueError("consumer_id contains invalid characters")
    return text


def _require_repo(value: str) -> str:
    text = value.strip()
    if not _REPOSITORY_RE.fullmatch(text):
        raise ValueError("repository_ref must be owner/repo")
    return text
