"""Application gateway: authenticate consumer → typed SurrealHandoffJournal ops.

Payload ``agent_id`` / ``repository_ref`` are never AuthN trust anchors. The
server derives ``RequestContext`` from the verified consumer token + grants.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from agent_brain.memory.handoff import HandoffEvent, SurrealHandoffJournal
from agent_brain.memory.handoff_auth import (
    HandoffCredentialStore,
    HandoffForbidden,
    HandoffOperation,
    RequestContext,
)

HANDOFF_CONTRACT_VERSION = "shared-memory-handoff/v1"


@dataclass(frozen=True, slots=True)
class HandoffGatewayResult:
    ok: bool
    contract: str
    context: RequestContext | None
    event: HandoffEvent | None = None
    events: tuple[HandoffEvent, ...] = ()
    error: str | None = None
    code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ok": self.ok,
            "contract": self.contract,
            "code": self.code,
            "error": self.error,
        }
        if self.context is not None:
            payload["context"] = {
                "consumer_id": self.context.consumer_id,
                "repository_ref": self.context.repository_ref,
                "grant_id": self.context.grant_id,
                "operations": sorted(op.value for op in self.context.operations),
                "token_hash_prefix": self.context.token_hash_prefix,
            }
        if self.event is not None:
            payload["event"] = self.event.to_dict()
        if self.events:
            payload["events"] = [item.to_dict() for item in self.events]
            payload["count"] = len(self.events)
        return payload


class HandoffGateway:
    """Least-privilege facade over the existing SurrealHandoffJournal."""

    def __init__(
        self,
        credentials: HandoffCredentialStore,
        journal: SurrealHandoffJournal,
    ) -> None:
        self._credentials = credentials
        self._journal = journal

    def append(self, token: str, payload: Mapping[str, Any]) -> HandoffGatewayResult:
        try:
            repository_ref = str(payload.get("repository_ref", ""))
            context = self._credentials.authenticate(
                token,
                repository_ref=repository_ref,
                operation=HandoffOperation.APPEND,
            )
            event = self._journal.append(
                repository_ref=context.repository_ref,
                agent_id=str(payload["agent_id"]),
                task_ref=str(payload["task_ref"]),
                status=str(payload["status"]),
                summary=str(payload["summary"]),
                next_step=str(payload["next_step"]),
                source_ref=str(payload["source_ref"]),
                idempotency_key=str(payload["idempotency_key"]),
            )
            return HandoffGatewayResult(
                ok=True,
                contract=HANDOFF_CONTRACT_VERSION,
                context=context,
                event=event,
                code="OK",
            )
        except HandoffForbidden as exc:
            return HandoffGatewayResult(
                ok=False,
                contract=HANDOFF_CONTRACT_VERSION,
                context=None,
                error=str(exc),
                code="FORBIDDEN",
            )
        except (KeyError, TypeError, ValueError) as exc:
            return HandoffGatewayResult(
                ok=False,
                contract=HANDOFF_CONTRACT_VERSION,
                context=None,
                error=str(exc),
                code="INVALID_REQUEST",
            )

    def recall(
        self,
        token: str,
        *,
        repository_ref: str,
        task_ref: str | None = None,
        limit: int = 20,
    ) -> HandoffGatewayResult:
        try:
            context = self._credentials.authenticate(
                token,
                repository_ref=repository_ref,
                operation=HandoffOperation.RECALL,
            )
            events = self._journal.recall(
                repository_ref=context.repository_ref,
                task_ref=task_ref,
                limit=limit,
            )
            return HandoffGatewayResult(
                ok=True,
                contract=HANDOFF_CONTRACT_VERSION,
                context=context,
                events=tuple(events),
                code="OK" if events else "EMPTY",
            )
        except HandoffForbidden as exc:
            return HandoffGatewayResult(
                ok=False,
                contract=HANDOFF_CONTRACT_VERSION,
                context=None,
                error=str(exc),
                code="FORBIDDEN",
            )
        except (TypeError, ValueError) as exc:
            return HandoffGatewayResult(
                ok=False,
                contract=HANDOFF_CONTRACT_VERSION,
                context=None,
                error=str(exc),
                code="INVALID_REQUEST",
            )
