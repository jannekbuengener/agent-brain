"""ImprovementManagementPort — Board-Manager mutations (#52).

Separated from ObservationStore. Observation writers must not receive this
surface. Merge uses #49 lineage helpers; lifecycle uses #46 transition matrix.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Protocol

from agent_brain.contracts.improvement import (
    IMPROVEMENT_WORK_REF_SCHEMA,
    Improvement,
    ImprovementLifecycle,
    ImprovementPriority,
    ImprovementWorkRef,
    WorkRefKind,
    require_lifecycle_transition,
)
from agent_brain.improvement.dedupe import merge_improvements as apply_merge
from agent_brain.improvement.errors import (
    ImprovementValidationError,
    InvalidImprovementScope,
)
from agent_brain.improvement.memory import InMemoryImprovementObservationStore
from agent_brain.improvement.surreal import SurrealImprovementObservationStore


@dataclass(frozen=True, slots=True)
class ManagementActor:
    """Authorized management actor identity (capability-gated by consumers)."""

    actor_id: str
    role: str = "improvement-board-manager"

    def __post_init__(self) -> None:
        if not self.actor_id.strip():
            raise ValueError("actor_id must not be blank")
        if self.role.strip() != "improvement-board-manager":
            raise InvalidImprovementScope(
                "management mutations require role=improvement-board-manager"
            )


class ImprovementManagementPort(Protocol):
    """Capability-gated management mutations for the Improvement Blackboard."""

    def set_priority(
        self,
        improvement_id: str,
        priority: ImprovementPriority | str,
        *,
        actor: ManagementActor,
        reason: str,
        expected_revision: int | None = None,
    ) -> Improvement: ...

    def transition_lifecycle(
        self,
        improvement_id: str,
        target: ImprovementLifecycle | str,
        *,
        actor: ManagementActor,
        reason: str,
        expected_revision: int | None = None,
    ) -> Improvement: ...

    def merge_improvements(
        self,
        target_improvement_id: str,
        source_improvement_ids: tuple[str, ...] | list[str],
        *,
        actor: ManagementActor,
        reason: str,
        evidence: tuple[str, ...] | list[str],
        merge_id: str,
        merged_at: datetime,
    ) -> Improvement: ...

    def link_work_item(
        self,
        improvement_id: str,
        work_ref: ImprovementWorkRef,
        *,
        actor: ManagementActor,
        expected_revision: int | None = None,
    ) -> Improvement: ...

    def link_pull_request(
        self,
        improvement_id: str,
        work_ref: ImprovementWorkRef,
        *,
        actor: ManagementActor,
        expected_revision: int | None = None,
    ) -> Improvement: ...

    def record_verification(
        self,
        improvement_id: str,
        work_ref: ImprovementWorkRef,
        *,
        actor: ManagementActor,
        expected_revision: int | None = None,
    ) -> Improvement: ...


class InMemoryImprovementManagementPort:
    """Management mutations over an in-memory observation store aggregates."""

    def __init__(self, store: InMemoryImprovementObservationStore) -> None:
        self._store = store
        self._lock = threading.RLock()

    def set_priority(
        self,
        improvement_id: str,
        priority: ImprovementPriority | str,
        *,
        actor: ManagementActor,
        reason: str,
        expected_revision: int | None = None,
    ) -> Improvement:
        _ = reason
        self._require_actor(actor)
        with self._lock:
            current = self._require_current(improvement_id, expected_revision)
            updated = replace(
                current,
                priority=ImprovementPriority(priority),
                revision=current.revision + 1,
            )
            self._store._improvements[improvement_id] = updated
            return updated

    def transition_lifecycle(
        self,
        improvement_id: str,
        target: ImprovementLifecycle | str,
        *,
        actor: ManagementActor,
        reason: str,
        expected_revision: int | None = None,
    ) -> Improvement:
        _ = reason
        self._require_actor(actor)
        with self._lock:
            current = self._require_current(improvement_id, expected_revision)
            target_state = ImprovementLifecycle(target)
            require_lifecycle_transition(current.lifecycle, target_state)
            updated = replace(
                current,
                lifecycle=target_state,
                revision=current.revision + 1,
            )
            self._store._improvements[improvement_id] = updated
            return updated

    def merge_improvements(
        self,
        target_improvement_id: str,
        source_improvement_ids: tuple[str, ...] | list[str],
        *,
        actor: ManagementActor,
        reason: str,
        evidence: tuple[str, ...] | list[str],
        merge_id: str,
        merged_at: datetime,
    ) -> Improvement:
        self._require_actor(actor)
        with self._lock:
            target = self._require_current(target_improvement_id, None)
            sources = []
            for source_id in source_improvement_ids:
                source = self._store.get_improvement(source_id)
                if source is None:
                    raise ImprovementValidationError(f"unknown source improvement: {source_id}")
                sources.append(source)
            merged, superseded, _lineage = apply_merge(
                target=target,
                sources=sources,
                actor_id=actor.actor_id,
                reason=reason,
                evidence=evidence,
                merged_at=merged_at,
                merge_id=merge_id,
            )
            self._store._improvements[merged.improvement_id] = merged
            for item in superseded:
                self._store._improvements[item.improvement_id] = item
                history = self._store._observations.get(item.improvement_id, [])
                target_history = self._store._observations.setdefault(merged.improvement_id, [])
                target_history.extend(history)
                self._store._observations[item.improvement_id] = []
            return self._store._refresh_aggregate(merged.improvement_id)

    def link_work_item(
        self,
        improvement_id: str,
        work_ref: ImprovementWorkRef,
        *,
        actor: ManagementActor,
        expected_revision: int | None = None,
    ) -> Improvement:
        return self._link_ref(
            improvement_id,
            work_ref,
            actor=actor,
            expected_revision=expected_revision,
            allowed_kinds={WorkRefKind.GITHUB_ISSUE},
        )

    def link_pull_request(
        self,
        improvement_id: str,
        work_ref: ImprovementWorkRef,
        *,
        actor: ManagementActor,
        expected_revision: int | None = None,
    ) -> Improvement:
        return self._link_ref(
            improvement_id,
            work_ref,
            actor=actor,
            expected_revision=expected_revision,
            allowed_kinds={WorkRefKind.GITHUB_PULL_REQUEST},
        )

    def record_verification(
        self,
        improvement_id: str,
        work_ref: ImprovementWorkRef,
        *,
        actor: ManagementActor,
        expected_revision: int | None = None,
    ) -> Improvement:
        return self._link_ref(
            improvement_id,
            work_ref,
            actor=actor,
            expected_revision=expected_revision,
            allowed_kinds={WorkRefKind.VERIFICATION},
        )

    def _link_ref(
        self,
        improvement_id: str,
        work_ref: ImprovementWorkRef,
        *,
        actor: ManagementActor,
        expected_revision: int | None,
        allowed_kinds: set[WorkRefKind],
    ) -> Improvement:
        self._require_actor(actor)
        if work_ref.kind not in allowed_kinds:
            raise ImprovementValidationError(
                f"work_ref.kind must be one of {[item.value for item in allowed_kinds]}"
            )
        with self._lock:
            current = self._require_current(improvement_id, expected_revision)
            for existing in current.work_refs:
                if (
                    existing.kind == work_ref.kind
                    and existing.repository_ref == work_ref.repository_ref
                    and existing.ref == work_ref.ref
                ):
                    return current
            updated = replace(
                current,
                work_refs=(*current.work_refs, work_ref),
                revision=current.revision + 1,
            )
            self._store._improvements[improvement_id] = updated
            return updated

    def _require_actor(self, actor: ManagementActor) -> None:
        if not isinstance(actor, ManagementActor):
            raise TypeError("actor must be a ManagementActor")
        self._store._ensure_available()

    def _require_current(
        self,
        improvement_id: str,
        expected_revision: int | None,
    ) -> Improvement:
        current = self._store.get_improvement(improvement_id)
        if current is None:
            raise ImprovementValidationError(f"unknown improvement: {improvement_id}")
        if expected_revision is not None and current.revision != expected_revision:
            raise ImprovementValidationError(
                f"revision conflict: expected {expected_revision}, got {current.revision}"
            )
        return current


class SurrealImprovementManagementPort:
    """Management mutations persisted through SurrealImprovementObservationStore."""

    def __init__(self, store: SurrealImprovementObservationStore) -> None:
        self._store = store
        self._lock = threading.RLock()

    def set_priority(
        self,
        improvement_id: str,
        priority: ImprovementPriority | str,
        *,
        actor: ManagementActor,
        reason: str,
        expected_revision: int | None = None,
    ) -> Improvement:
        _ = reason
        self._require_actor(actor)
        with self._lock:
            current = self._require_current(improvement_id, expected_revision)
            updated = replace(
                current,
                priority=ImprovementPriority(priority),
                revision=current.revision + 1,
            )
            return self._store.replace_improvement_aggregate(
                updated,
                expected_revision=current.revision,
            )

    def transition_lifecycle(
        self,
        improvement_id: str,
        target: ImprovementLifecycle | str,
        *,
        actor: ManagementActor,
        reason: str,
        expected_revision: int | None = None,
    ) -> Improvement:
        _ = reason
        self._require_actor(actor)
        with self._lock:
            current = self._require_current(improvement_id, expected_revision)
            target_state = ImprovementLifecycle(target)
            require_lifecycle_transition(current.lifecycle, target_state)
            updated = replace(
                current,
                lifecycle=target_state,
                revision=current.revision + 1,
            )
            return self._store.replace_improvement_aggregate(
                updated,
                expected_revision=current.revision,
            )

    def merge_improvements(
        self,
        target_improvement_id: str,
        source_improvement_ids: tuple[str, ...] | list[str],
        *,
        actor: ManagementActor,
        reason: str,
        evidence: tuple[str, ...] | list[str],
        merge_id: str,
        merged_at: datetime,
    ) -> Improvement:
        self._require_actor(actor)
        with self._lock:
            target = self._require_current(target_improvement_id, None)
            sources = []
            for source_id in source_improvement_ids:
                source = self._store.get_improvement(source_id)
                if source is None:
                    raise ImprovementValidationError(f"unknown source improvement: {source_id}")
                sources.append(source)
            merged, superseded, _lineage = apply_merge(
                target=target,
                sources=sources,
                actor_id=actor.actor_id,
                reason=reason,
                evidence=evidence,
                merged_at=merged_at,
                merge_id=merge_id,
            )
            self._store.replace_improvement_aggregate(
                merged,
                expected_revision=target.revision,
            )
            for item in superseded:
                self._store.replace_improvement_aggregate(item, expected_revision=None)
                self._store.transfer_observations(
                    source_improvement_id=item.improvement_id,
                    target_improvement_id=merged.improvement_id,
                )
            return self._store._refresh_aggregate(merged.improvement_id)

    def link_work_item(
        self,
        improvement_id: str,
        work_ref: ImprovementWorkRef,
        *,
        actor: ManagementActor,
        expected_revision: int | None = None,
    ) -> Improvement:
        return self._link_ref(
            improvement_id,
            work_ref,
            actor=actor,
            expected_revision=expected_revision,
            allowed_kinds={WorkRefKind.GITHUB_ISSUE},
        )

    def link_pull_request(
        self,
        improvement_id: str,
        work_ref: ImprovementWorkRef,
        *,
        actor: ManagementActor,
        expected_revision: int | None = None,
    ) -> Improvement:
        return self._link_ref(
            improvement_id,
            work_ref,
            actor=actor,
            expected_revision=expected_revision,
            allowed_kinds={WorkRefKind.GITHUB_PULL_REQUEST},
        )

    def record_verification(
        self,
        improvement_id: str,
        work_ref: ImprovementWorkRef,
        *,
        actor: ManagementActor,
        expected_revision: int | None = None,
    ) -> Improvement:
        return self._link_ref(
            improvement_id,
            work_ref,
            actor=actor,
            expected_revision=expected_revision,
            allowed_kinds={WorkRefKind.VERIFICATION},
        )

    def _link_ref(
        self,
        improvement_id: str,
        work_ref: ImprovementWorkRef,
        *,
        actor: ManagementActor,
        expected_revision: int | None,
        allowed_kinds: set[WorkRefKind],
    ) -> Improvement:
        self._require_actor(actor)
        if work_ref.kind not in allowed_kinds:
            raise ImprovementValidationError(
                f"work_ref.kind must be one of {[item.value for item in allowed_kinds]}"
            )
        with self._lock:
            current = self._require_current(improvement_id, expected_revision)
            for existing in current.work_refs:
                if (
                    existing.kind == work_ref.kind
                    and existing.repository_ref == work_ref.repository_ref
                    and existing.ref == work_ref.ref
                ):
                    return current
            updated = replace(
                current,
                work_refs=(*current.work_refs, work_ref),
                revision=current.revision + 1,
            )
            return self._store.replace_improvement_aggregate(
                updated,
                expected_revision=current.revision,
            )

    def _require_actor(self, actor: ManagementActor) -> None:
        if not isinstance(actor, ManagementActor):
            raise TypeError("actor must be a ManagementActor")
        self._store._ensure_available()

    def _require_current(
        self,
        improvement_id: str,
        expected_revision: int | None,
    ) -> Improvement:
        current = self._store.get_improvement(improvement_id)
        if current is None:
            raise ImprovementValidationError(f"unknown improvement: {improvement_id}")
        if expected_revision is not None and current.revision != expected_revision:
            raise ImprovementValidationError(
                f"revision conflict: expected {expected_revision}, got {current.revision}"
            )
        return current


def board_manager_actor(actor_id: str) -> ManagementActor:
    """Factory for the only V1 role authorized for management writes."""
    return ManagementActor(actor_id=actor_id, role="improvement-board-manager")


def github_issue_work_ref(
    *,
    repository_ref: str,
    issue_number: str,
    url: str | None = None,
    linked_at: datetime | None = None,
) -> ImprovementWorkRef:
    return ImprovementWorkRef(
        schema_version=IMPROVEMENT_WORK_REF_SCHEMA,
        kind=WorkRefKind.GITHUB_ISSUE,
        repository_ref=repository_ref,
        ref=str(issue_number),
        url=url,
        linked_at=linked_at,
    )
