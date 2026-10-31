"""In-memory ImprovementObservationStore for contract/fixture tests.

Not a production persistence choice — #48 selects durable storage behind the
same port. This adapter proves append-only, idempotent, concurrent-safe
observation semantics without touching KnowledgeStore or MemoryStore.
"""

from __future__ import annotations

import threading
from dataclasses import replace

from agent_brain.contracts.improvement import (
    Improvement,
    ImprovementLifecycle,
    ImprovementObservation,
    build_improvement_id,
    derive_recurrence,
    normalize_root_cause_key,
)
from agent_brain.improvement.errors import (
    ImprovementIdentityAmbiguous,
    ImprovementStoreUnavailable,
    ImprovementValidationError,
    InvalidImprovementScope,
)
from agent_brain.improvement.ports import SubmitObservationResult


class InMemoryImprovementObservationStore:
    """Thread-safe append-only observation store with derived aggregates."""

    # Explicitly absent management surface (asserted by tests).
    MANAGEMENT_METHODS = frozenset(
        {
            "set_priority",
            "transition_lifecycle",
            "merge_improvements",
            "link_work_item",
            "link_pull_request",
            "record_verification",
        }
    )

    def __init__(self, *, available: bool = True) -> None:
        self._available = available
        self._lock = threading.RLock()
        self._improvements: dict[str, Improvement] = {}
        self._observations: dict[str, list[ImprovementObservation]] = {}
        self._idempotency: dict[str, SubmitObservationResult] = {}

    def mark_unavailable(self) -> None:
        self._available = False

    def mark_available(self) -> None:
        self._available = True

    def _ensure_available(self) -> None:
        if not self._available:
            raise ImprovementStoreUnavailable("improvement observation store unavailable")

    def submit_observation(self, observation: ImprovementObservation) -> SubmitObservationResult:
        if not isinstance(observation, ImprovementObservation):
            raise TypeError("observation must be an ImprovementObservation")
        self._ensure_available()

        with self._lock:
            existing = self._idempotency.get(observation.idempotency_key)
            if existing is not None:
                current = self._improvements.get(existing.improvement.improvement_id)
                return SubmitObservationResult(
                    observation=existing.observation,
                    improvement=current if current is not None else existing.improvement,
                    created_new_observation=False,
                    created_new_improvement=False,
                )

            improvement_id, root_cause_key = self._resolve_identity(observation)
            bound = (
                observation
                if observation.improvement_id == improvement_id
                and observation.root_cause_key == root_cause_key
                else replace(
                    observation,
                    improvement_id=improvement_id,
                    root_cause_key=root_cause_key,
                )
            )

            created_new_improvement = improvement_id not in self._improvements
            if created_new_improvement:
                improvement = self._new_improvement_from_observation(bound, improvement_id, root_cause_key)
                self._improvements[improvement_id] = improvement
                self._observations[improvement_id] = []
            else:
                current = self._improvements[improvement_id]
                if current.skill_id != bound.skill_id:
                    raise InvalidImprovementScope(
                        "observation skill_id does not match existing improvement"
                    )
                if (
                    bound.repository_ref is not None
                    and current.repository_refs
                    and bound.repository_ref not in current.repository_refs
                ):
                    # Allow attaching a new repo ref by updating aggregate below.
                    pass

            history = self._observations[improvement_id]
            if any(item.observation_id == bound.observation_id for item in history):
                raise ImprovementValidationError(
                    f"observation_id already exists: {bound.observation_id}"
                )
            history.append(bound)

            improvement = self._refresh_aggregate(improvement_id)
            result = SubmitObservationResult(
                observation=bound,
                improvement=improvement,
                created_new_observation=True,
                created_new_improvement=created_new_improvement,
            )
            self._idempotency[bound.idempotency_key] = result
            return result

    def get_improvement(self, improvement_id: str) -> Improvement | None:
        self._ensure_available()
        with self._lock:
            return self._improvements.get(improvement_id)

    def list_improvements(
        self,
        *,
        skill_id: str | None = None,
        repository_ref: str | None = None,
        lifecycle: ImprovementLifecycle | str | None = None,
    ) -> tuple[Improvement, ...]:
        self._ensure_available()
        lifecycle_filter: ImprovementLifecycle | None = None
        if lifecycle is not None:
            lifecycle_filter = ImprovementLifecycle(lifecycle)
        with self._lock:
            items = list(self._improvements.values())
        if skill_id is not None:
            items = [item for item in items if item.skill_id == skill_id]
        if repository_ref is not None:
            items = [item for item in items if repository_ref in item.repository_refs]
        if lifecycle_filter is not None:
            items = [item for item in items if item.lifecycle == lifecycle_filter]
        items.sort(key=lambda item: (item.skill_id, item.root_cause_key, item.improvement_id))
        return tuple(items)

    def list_observations(self, improvement_id: str) -> tuple[ImprovementObservation, ...]:
        self._ensure_available()
        with self._lock:
            history = self._observations.get(improvement_id)
            if history is None:
                return ()
            return tuple(history)

    def find_candidates(
        self,
        *,
        skill_id: str,
        root_cause_key: str | None = None,
        repository_ref: str | None = None,
    ) -> tuple[Improvement, ...]:
        self._ensure_available()
        if not skill_id or not str(skill_id).strip():
            raise InvalidImprovementScope("skill_id is required for candidate lookup")
        normalized_key = (
            None if root_cause_key is None else normalize_root_cause_key(root_cause_key)
        )
        with self._lock:
            items = [
                item
                for item in self._improvements.values()
                if item.skill_id == skill_id
                and (normalized_key is None or item.root_cause_key == normalized_key)
                and (repository_ref is None or repository_ref in item.repository_refs)
            ]
        items.sort(key=lambda item: item.improvement_id)
        return tuple(items)

    def _resolve_identity(
        self,
        observation: ImprovementObservation,
    ) -> tuple[str, str]:
        if observation.root_cause_key is None and observation.improvement_id is None:
            raise ImprovementIdentityAmbiguous(
                "observation requires root_cause_key or improvement_id"
            )

        if observation.root_cause_key is not None:
            root_cause_key = normalize_root_cause_key(observation.root_cause_key)
            improvement_id = build_improvement_id(
                skill_id=observation.skill_id,
                root_cause_key=root_cause_key,
            )
            if (
                observation.improvement_id is not None
                and observation.improvement_id != improvement_id
            ):
                raise InvalidImprovementScope(
                    "improvement_id does not match skill_id/root_cause_key identity"
                )
            return improvement_id, root_cause_key

        assert observation.improvement_id is not None
        existing = self._improvements.get(observation.improvement_id)
        if existing is None:
            raise ImprovementIdentityAmbiguous(
                "improvement_id unknown and root_cause_key missing; refusing to invent identity"
            )
        return existing.improvement_id, existing.root_cause_key

    def _new_improvement_from_observation(
        self,
        observation: ImprovementObservation,
        improvement_id: str,
        root_cause_key: str,
    ) -> Improvement:
        repo_refs = () if observation.repository_ref is None else (observation.repository_ref,)
        task_refs = () if observation.task_ref is None else (observation.task_ref,)
        return Improvement(
            schema_version="improvement/v1",
            improvement_id=improvement_id,
            skill_id=observation.skill_id,
            root_cause_key=root_cause_key,
            summary=observation.observation,
            recommendation=observation.recommendation,
            expected_benefit="pending-board-validation",
            lifecycle=ImprovementLifecycle.NEW,
            first_seen=observation.timestamp,
            last_seen=observation.timestamp,
            skill_version_ref=observation.skill_version_ref,
            confidence=observation.confidence,
            recurrence=0,
            repository_refs=repo_refs,
            task_refs=task_refs,
            revision=1,
        )

    def _refresh_aggregate(self, improvement_id: str) -> Improvement:
        current = self._improvements[improvement_id]
        history = self._observations[improvement_id]
        recurrence = derive_recurrence(len(history))
        first_seen = min(item.timestamp for item in history)
        last_seen = max(item.timestamp for item in history)
        repository_refs = tuple(
            dict.fromkeys(
                [
                    *current.repository_refs,
                    *[
                        item.repository_ref
                        for item in history
                        if item.repository_ref is not None
                    ],
                ]
            )
        )
        task_refs = tuple(
            dict.fromkeys(
                [
                    *current.task_refs,
                    *[item.task_ref for item in history if item.task_ref is not None],
                ]
            )
        )
        lifecycle = current.lifecycle
        if lifecycle == ImprovementLifecycle.NEW and recurrence >= 2:
            lifecycle = ImprovementLifecycle.RECURRING

        latest = history[-1]
        updated = Improvement(
            schema_version=current.schema_version,
            improvement_id=current.improvement_id,
            skill_id=current.skill_id,
            root_cause_key=current.root_cause_key,
            summary=current.summary,
            recommendation=current.recommendation,
            expected_benefit=current.expected_benefit,
            lifecycle=lifecycle,
            first_seen=first_seen,
            last_seen=last_seen,
            skill_version_ref=current.skill_version_ref or latest.skill_version_ref,
            confidence=latest.confidence if latest.confidence is not None else current.confidence,
            priority=current.priority,
            recurrence=recurrence,
            repository_refs=repository_refs,
            task_refs=task_refs,
            related_skill_ids=current.related_skill_ids,
            relations=current.relations,
            work_refs=current.work_refs,
            merge_lineage=current.merge_lineage,
            revision=current.revision + 1,
            temporal=current.temporal,
            resolution=current.resolution,
            superseded_by_improvement_id=current.superseded_by_improvement_id,
            aliases=current.aliases,
        )
        self._improvements[improvement_id] = updated
        return updated
