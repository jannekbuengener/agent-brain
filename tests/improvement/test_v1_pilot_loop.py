"""V1 Skill Improvement Blackboard pilot loop evidence (#52 / workforce#54)."""

from __future__ import annotations

import inspect
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from agent_brain.contracts.improvement import (
    IMPROVEMENT_OBSERVATION_SCHEMA,
    IMPROVEMENT_WORK_REF_SCHEMA,
    DedupeRelationKind,
    ImprovementLifecycle,
    ImprovementObservation,
    ImprovementWorkRef,
    WorkRefKind,
)
from agent_brain.improvement import (
    InMemoryImprovementObservationStore,
    SqliteImprovementObservationStore,
)
from agent_brain.improvement.cli import main as cli_main
from agent_brain.improvement.dedupe import assess_observation
from agent_brain.improvement.errors import InvalidImprovementScope
from agent_brain.improvement.management import (
    InMemoryImprovementManagementPort,
    ManagementActor,
    board_manager_actor,
    github_issue_work_ref,
)
from agent_brain.improvement.projection import (
    ImprovementMarkdownProjection,
    compute_source_hash,
)


PILOT_SKILLS = (
    "cursor-meta-epic-executor",
    "cloudflare-one",
    "wrangler",
)

# 10 distinct root causes across the three pilot skills.
PILOT_ROOTS: tuple[tuple[str, str], ...] = (
    ("cursor-meta-epic-executor", "host-visual-evidence-floor"),
    ("cursor-meta-epic-executor", "authority-reconciliation-gap"),
    ("cursor-meta-epic-executor", "reuse-before-build-skip"),
    ("cloudflare-one", "tunnel-route-drift"),
    ("cloudflare-one", "access-policy-overlap"),
    ("cloudflare-one", "device-posture-stale"),
    ("wrangler", "binding-name-collision"),
    ("wrangler", "secret-sync-lag"),
    ("wrangler", "env-var-drift"),
    ("wrangler", "cli-projection-export-missing"),
)


def _ts(hour: int = 12, second: int = 0) -> datetime:
    return datetime(2026, 10, 31, hour, 0, second, tzinfo=UTC)


def _obs(
    *,
    observation_id: str,
    skill_id: str,
    root: str,
    key: str,
    agent_id: str = "agent-a",
    hour: int = 12,
    second: int = 0,
    observation: str | None = None,
    recommendation: str | None = None,
) -> ImprovementObservation:
    return ImprovementObservation(
        schema_version=IMPROVEMENT_OBSERVATION_SCHEMA,
        observation_id=observation_id,
        agent_id=agent_id,
        run_id=f"run-{observation_id}",
        skill_id=skill_id,
        observation=observation or f"observation text for {observation_id} / {root}",
        recommendation=recommendation or f"recommend fix for {root}",
        evidence=(f"evidence::{observation_id}",),
        timestamp=_ts(hour, second),
        idempotency_key=key,
        root_cause_key=root,
        repository_ref="jannekbuengener/agent-brain",
    )


def _seed_twenty_events(store: SqliteImprovementObservationStore | InMemoryImprovementObservationStore) -> None:
    """Seed 10 improvements with ≥2 observations each (≥20 events)."""
    for index, (skill_id, root) in enumerate(PILOT_ROOTS, start=1):
        store.submit_observation(
            _obs(
                observation_id=f"obs-{index:02d}-a",
                skill_id=skill_id,
                root=root,
                key=f"idem-{index:02d}-a",
                agent_id="agent-a",
                hour=10,
                second=index,
            )
        )
        store.submit_observation(
            _obs(
                observation_id=f"obs-{index:02d}-b",
                skill_id=skill_id,
                root=root,
                key=f"idem-{index:02d}-b",
                agent_id="agent-b",
                hour=11,
                second=index,
                observation=f"alternate wording for {root}",
                recommendation=f"alternate recommendation for {root}",
            )
        )


def test_v1_pilot_loop_end_to_end(tmp_path: Path) -> None:
    db_path = tmp_path / "pilot.sqlite3"
    store = SqliteImprovementObservationStore(db_path)

    # --- seed: 3 skills, 10 improvements, ≥20 observations ---
    _seed_twenty_events(store)
    improvements = store.list_improvements()
    assert len(improvements) == 10
    skills = {item.skill_id for item in improvements}
    assert skills == set(PILOT_SKILLS)

    total_events = sum(len(store.list_observations(item.improvement_id)) for item in improvements)
    assert total_events >= 20

    # --- true duplicate identity (already satisfied by dual seed) ---
    handoff_id = next(
        item.improvement_id
        for item in improvements
        if item.root_cause_key == "cli-projection-export-missing"
    )
    handoff = store.get_improvement(handoff_id)
    assert handoff is not None
    assert handoff.recurrence == 2
    assert len(store.list_observations(handoff_id)) == 2

    # --- similar-but-different: no auto-merge ---
    similar = _obs(
        observation_id="obs-similar",
        skill_id="cursor-meta-epic-executor",
        root="owner-visual-self-pass-forbidden",
        key="idem-similar",
        observation="Screenshots taken before layout settled for visual acceptance.",
        recommendation="Wait for stable geometry before visual acceptance screenshots.",
    )
    assessment = assess_observation(similar, store.list_improvements())
    assert assessment.auto_merge_allowed is False
    assert assessment.kind != DedupeRelationKind.EXACT_IDENTITY
    assert assessment.kind in {
        DedupeRelationKind.POSSIBLE_DUPLICATE,
        DedupeRelationKind.RELATED,
        "NEW",
    }
    before_count = len(store.list_improvements())
    store.submit_observation(similar)
    assert len(store.list_improvements()) == before_count + 1

    # --- concurrent writers: 0 lost events ---
    base = datetime(2026, 10, 31, 15, 0, tzinfo=UTC)
    submitted_keys: list[str] = []

    def write(index: int) -> str:
        key = f"concurrent-{index}"
        store.submit_observation(
            ImprovementObservation(
                schema_version=IMPROVEMENT_OBSERVATION_SCHEMA,
                observation_id=f"obs-concurrent-{index}",
                agent_id=f"agent-{'a' if index % 2 == 0 else 'b'}",
                run_id=f"run-concurrent-{index}",
                skill_id="cloudflare-one",
                observation=f"concurrent observation {index}",
                recommendation="stabilize tunnel routes",
                evidence=(f"evidence::concurrent-{index}",),
                timestamp=base + timedelta(seconds=index),
                idempotency_key=key,
                root_cause_key="tunnel-route-drift",
                repository_ref="jannekbuengener/agent-brain",
            )
        )
        return key

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(write, index) for index in range(8)]
        for future in as_completed(futures):
            submitted_keys.append(future.result())

    assert len(submitted_keys) == 8
    tunnel_id = next(
        item.improvement_id
        for item in store.list_improvements()
        if item.root_cause_key == "tunnel-route-drift"
    )
    tunnel_events = store.list_observations(tunnel_id)
    concurrent_keys = {event.idempotency_key for event in tunnel_events if event.idempotency_key.startswith("concurrent-")}
    assert concurrent_keys == set(submitted_keys)

    # --- idempotent retry ---
    before = len(store.list_observations(tunnel_id))
    retry = store.submit_observation(
        ImprovementObservation(
            schema_version=IMPROVEMENT_OBSERVATION_SCHEMA,
            observation_id="obs-concurrent-0-retry",
            agent_id="agent-a",
            run_id="run-retry",
            skill_id="cloudflare-one",
            observation="concurrent observation 0",
            recommendation="stabilize tunnel routes",
            evidence=("evidence::concurrent-0",),
            timestamp=base,
            idempotency_key="concurrent-0",
            root_cause_key="tunnel-route-drift",
            repository_ref="jannekbuengener/agent-brain",
        )
    )
    assert retry.created_new_observation is False
    assert len(store.list_observations(tunnel_id)) == before

    # --- authority separation ---
    with pytest.raises(InvalidImprovementScope):
        ManagementActor(actor_id="scout-1", role="quality-scout")

    # Management port needs InMemory store adapter — copy aggregates via reopen pattern:
    # Use in-memory management against a fresh in-memory mirror for lifecycle path,
    # after proving sqlite persistence above. For lifecycle we operate on sqlite via
    # InMemoryImprovementManagementPort only accepts InMemory store — mirror handoff.
    mem = InMemoryImprovementObservationStore()
    for event in store.list_observations(handoff_id):
        mem.submit_observation(event)
    # Ensure recurrence >= 2 / RECURRING
    mirrored = mem.get_improvement(handoff_id)
    assert mirrored is not None
    assert mirrored.lifecycle is ImprovementLifecycle.RECURRING

    mgr = InMemoryImprovementManagementPort(mem)
    actor = board_manager_actor("board-pilot-1")
    validated = mgr.transition_lifecycle(
        handoff_id,
        ImprovementLifecycle.VALIDATED,
        actor=actor,
        reason="pilot validated CLI projection gap",
    )
    assert validated.lifecycle is ImprovementLifecycle.VALIDATED

    planned = mgr.transition_lifecycle(
        handoff_id,
        ImprovementLifecycle.PLANNED,
        actor=actor,
        reason="owning repo agent-brain clear",
    )
    linked = mgr.link_work_item(
        handoff_id,
        github_issue_work_ref(
            repository_ref="jannekbuengener/agent-brain",
            issue_number="60",
            url="https://github.com/jannekbuengener/agent-brain/issues/60",
            linked_at=datetime(2026, 10, 31, 18, 0, tzinfo=UTC),
        ),
        actor=actor,
        expected_revision=planned.revision,
    )
    assert any(ref.kind is WorkRefKind.GITHUB_ISSUE and ref.ref == "60" for ref in linked.work_refs)

    # closed issue alone ≠ VERIFIED
    assert linked.lifecycle is not ImprovementLifecycle.VERIFIED

    implemented = mgr.transition_lifecycle(
        handoff_id,
        ImprovementLifecycle.IMPLEMENTED,
        actor=actor,
        reason="PR merged implementing CLI project export",
    )
    assert implemented.lifecycle is ImprovementLifecycle.IMPLEMENTED

    mgr.link_pull_request(
        handoff_id,
        ImprovementWorkRef(
            schema_version=IMPROVEMENT_WORK_REF_SCHEMA,
            kind=WorkRefKind.GITHUB_PULL_REQUEST,
            repository_ref="jannekbuengener/agent-brain",
            ref="TBD",
            url=None,
        ),
        actor=actor,
    )
    mgr.record_verification(
        handoff_id,
        ImprovementWorkRef(
            schema_version=IMPROVEMENT_WORK_REF_SCHEMA,
            kind=WorkRefKind.VERIFICATION,
            repository_ref="jannekbuengener/agent-brain",
            ref="pytest-tests/improvement",
        ),
        actor=actor,
    )
    verified = mgr.transition_lifecycle(
        handoff_id,
        ImprovementLifecycle.VERIFIED,
        actor=actor,
        reason="current verification evidence attached",
    )
    assert verified.lifecycle is ImprovementLifecycle.VERIFIED

    # --- projection rebuildable ---
    # Re-seed a clean 10-improvement sqlite for deterministic projection of the pilot floor.
    proj_db = tmp_path / "proj.sqlite3"
    proj_store = SqliteImprovementObservationStore(proj_db)
    _seed_twenty_events(proj_store)
    assert len(proj_store.list_improvements()) == 10
    generated_at = datetime(2026, 10, 31, 20, 0, tzinfo=UTC)
    vault_a = tmp_path / "vault-a"
    vault_b = tmp_path / "vault-b"
    projection = ImprovementMarkdownProjection()
    first = projection.export(proj_store, vault_a, generated_at=generated_at)
    second = projection.export(proj_store, vault_b, generated_at=generated_at)
    assert first.source_hash == second.source_hash == compute_source_hash(proj_store)
    files_a = {
        path.relative_to(vault_a).as_posix(): path.read_bytes()
        for path in vault_a.rglob("*")
        if path.is_file()
    }
    files_b = {
        path.relative_to(vault_b).as_posix(): path.read_bytes()
        for path in vault_b.rglob("*")
        if path.is_file()
    }
    assert files_a == files_b
    assert not hasattr(projection, "import_from_vault")
    public = {
        name
        for name, _ in inspect.getmembers(projection, predicate=callable)
        if not name.startswith("_")
    }
    assert public <= {"export"}

    # --- CLI project subcommand (capability-gated read) ---
    vault_cli = tmp_path / "vault-cli"
    rc = cli_main(
        [
            "project",
            "--actor",
            "operator-1",
            "--run",
            "pilot-run",
            "--cap",
            "improvement_read",
            "--db",
            str(proj_db),
            "--vault",
            str(vault_cli),
            "--generated-at",
            "2026-10-31T20:00:00Z",
        ]
    )
    assert rc == 0
    assert (vault_cli / "blackboard" / "index.md").is_file()

    denied = cli_main(
        [
            "project",
            "--actor",
            "operator-1",
            "--run",
            "pilot-run",
            "--cap",
            "improvement_observation_write",
            "--db",
            str(proj_db),
            "--vault",
            str(tmp_path / "vault-denied"),
            "--generated-at",
            "2026-10-31T20:00:00Z",
        ]
    )
    assert denied == 2

    # --- Memory/Knowledge boundaries ---
    improvement_pkg = Path(__file__).resolve().parents[2] / "src" / "agent_brain" / "improvement"
    for path in improvement_pkg.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "remember(" not in text
        assert "brain.write(" not in text


def test_v1_pilot_concurrent_barrier_two_agents(tmp_path: Path) -> None:
    """Explicit two-agent concurrent write barrier with zero loss."""
    store = SqliteImprovementObservationStore(tmp_path / "barrier.sqlite3")
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def agent_worker(agent_id: str, start: int) -> None:
        try:
            barrier.wait(timeout=5)
            for offset in range(5):
                index = start + offset
                store.submit_observation(
                    ImprovementObservation(
                        schema_version=IMPROVEMENT_OBSERVATION_SCHEMA,
                        observation_id=f"barrier-{agent_id}-{index}",
                        agent_id=agent_id,
                        run_id=f"run-{agent_id}-{index}",
                        skill_id="wrangler",
                        observation=f"barrier event {index}",
                        recommendation="keep writes append-only",
                        evidence=(f"evidence::barrier-{index}",),
                        timestamp=_ts(16, index),
                        idempotency_key=f"barrier-{index}",
                        root_cause_key="secret-sync-lag",
                        repository_ref="jannekbuengener/agent-brain",
                    )
                )
        except BaseException as exc:  # noqa: BLE001 - collect worker errors
            errors.append(exc)

    threads = [
        threading.Thread(target=agent_worker, args=("agent-a", 0)),
        threading.Thread(target=agent_worker, args=("agent-b", 5)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert errors == []
    improvement_id = next(
        item.improvement_id
        for item in store.list_improvements()
        if item.root_cause_key == "secret-sync-lag"
    )
    events = store.list_observations(improvement_id)
    assert len(events) == 10
    assert {event.idempotency_key for event in events} == {f"barrier-{i}" for i in range(10)}
