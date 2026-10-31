"""Read-only Markdown/Obsidian projection of the Improvement Blackboard (#51)."""

from __future__ import annotations

import inspect
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agent_brain.contracts.improvement import (
    IMPROVEMENT_OBSERVATION_SCHEMA,
    IMPROVEMENT_WORK_REF_SCHEMA,
    DedupeRelationKind,
    ImprovementLifecycle,
    ImprovementObservation,
    ImprovementPriority,
    ImprovementRelation,
    ImprovementWorkRef,
    WorkRefKind,
    build_improvement_id,
)
from agent_brain.improvement import InMemoryImprovementObservationStore
from agent_brain.improvement.errors import ImprovementProjectionConflict
from agent_brain.improvement.management import (
    InMemoryImprovementManagementPort,
    board_manager_actor,
)
from agent_brain.improvement.projection import (
    PROJECTION_VERSION,
    ImprovementMarkdownProjection,
    compute_source_hash,
    improvement_markdown_stem,
    repository_markdown_stem,
)


def _ts(hour: int = 12) -> datetime:
    return datetime(2026, 10, 31, hour, 0, tzinfo=UTC)


def _obs(
    observation_id: str,
    *,
    skill_id: str,
    root: str,
    key: str,
    repository_ref: str | None = "jannekbuengener/agent-workforce",
    hour: int = 12,
) -> ImprovementObservation:
    return ImprovementObservation(
        schema_version=IMPROVEMENT_OBSERVATION_SCHEMA,
        observation_id=observation_id,
        agent_id="agent-a",
        run_id=f"run-{observation_id}",
        skill_id=skill_id,
        observation=f"observation text for {observation_id}",
        recommendation=f"recommend {root}",
        evidence=(f"evidence::{observation_id}",),
        timestamp=_ts(hour),
        idempotency_key=key,
        root_cause_key=root,
        repository_ref=repository_ref,
    )


def _seed_ten(store: InMemoryImprovementObservationStore) -> list[str]:
    roots = [
        ("cursor-meta-epic-executor", "host-visual-evidence-floor"),
        ("cursor-meta-epic-executor", "authority-reconciliation-gap"),
        ("cursor-meta-epic-executor", "reuse-before-build-skip"),
        ("cloudflare-one", "tunnel-route-drift"),
        ("cloudflare-one", "access-policy-overlap"),
        ("wrangler", "binding-name-collision"),
        ("wrangler", "secret-sync-lag"),
        ("durable-objects", "alarm-retry-storm"),
        ("agents-sdk", "tool-schema-drift"),
        ("origin", "mirror-lag-detection"),
    ]
    ids: list[str] = []
    for index, (skill_id, root) in enumerate(roots, start=1):
        result = store.submit_observation(
            _obs(
                f"obs-{index:02d}",
                skill_id=skill_id,
                root=root,
                key=f"idem-{index:02d}",
                hour=10 + (index % 5),
            )
        )
        ids.append(result.improvement.improvement_id)
        if index % 3 == 0:
            store.submit_observation(
                _obs(
                    f"obs-{index:02d}-b",
                    skill_id=skill_id,
                    root=root,
                    key=f"idem-{index:02d}-b",
                    hour=15,
                )
            )
    return ids


def test_projection_has_no_write_back_api() -> None:
    projection = ImprovementMarkdownProjection()
    forbidden = (
        "import_from_vault",
        "import_vault",
        "apply_vault_edits",
        "write_back",
        "sync_from_markdown",
        "upsert_from_markdown",
        "merge_vault_into_store",
    )
    for name in forbidden:
        assert not hasattr(projection, name)
    public = {
        name
        for name, _ in inspect.getmembers(projection, predicate=callable)
        if not name.startswith("_")
    }
    assert "export" in public
    assert public <= {"export"}


def test_export_ten_improvements_deterministically(tmp_path: Path) -> None:
    store = InMemoryImprovementObservationStore()
    ids = _seed_ten(store)
    assert len(ids) == 10

    generated_at = datetime(2026, 10, 31, 18, 0, tzinfo=UTC)
    projection = ImprovementMarkdownProjection()
    first = projection.export(store, tmp_path / "a", generated_at=generated_at)
    second = projection.export(store, tmp_path / "b", generated_at=generated_at)

    assert first.source_hash == second.source_hash
    assert first.source_hash == compute_source_hash(store)
    assert first.projection_version == PROJECTION_VERSION

    files_a = {
        path.relative_to(tmp_path / "a").as_posix(): path.read_bytes()
        for path in (tmp_path / "a").rglob("*")
        if path.is_file()
    }
    files_b = {
        path.relative_to(tmp_path / "b").as_posix(): path.read_bytes()
        for path in (tmp_path / "b").rglob("*")
        if path.is_file()
    }
    assert files_a == files_b
    assert len(files_a) >= 10

    for improvement_id in ids:
        stem = improvement_markdown_stem(improvement_id)
        path = tmp_path / "a" / "blackboard" / "improvements" / f"{stem}.md"
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n")
        assert f"improvement_id: {improvement_id}" in text
        assert f"projection_version: {PROJECTION_VERSION}" in text
        assert f"source_hash: {first.source_hash}" in text
        assert "generated_at:" in text


def test_frontmatter_links_and_observation_history(tmp_path: Path) -> None:
    store = InMemoryImprovementObservationStore()
    first_id = store.submit_observation(
        _obs(
            "obs-a",
            skill_id="cursor-meta-epic-executor",
            root="host-visual-evidence-floor",
            key="k-a",
        )
    ).improvement.improvement_id
    second_id = store.submit_observation(
        _obs(
            "obs-b",
            skill_id="cursor-meta-epic-executor",
            root="authority-reconciliation-gap",
            key="k-b",
            hour=13,
        )
    ).improvement.improvement_id
    store.submit_observation(
        _obs(
            "obs-a2",
            skill_id="cursor-meta-epic-executor",
            root="host-visual-evidence-floor",
            key="k-a2",
            hour=14,
        )
    )
    first = store.get_improvement(first_id)
    assert first is not None

    related = ImprovementRelation(
        related_improvement_id=second_id,
        kind=DedupeRelationKind.RELATED,
        reason="shared skill scope",
    )
    store._improvements[first_id] = replace(
        first,
        relations=(related,),
        priority=ImprovementPriority.HIGH,
        related_skill_ids=("origin",),
        work_refs=(
            ImprovementWorkRef(
                schema_version=IMPROVEMENT_WORK_REF_SCHEMA,
                kind=WorkRefKind.GITHUB_ISSUE,
                repository_ref="jannekbuengener/agent-workforce",
                ref="44",
                url="https://github.com/jannekbuengener/agent-workforce/issues/44",
            ),
        ),
        revision=first.revision + 1,
    )

    mgr = InMemoryImprovementManagementPort(store)
    mgr.transition_lifecycle(
        first_id,
        ImprovementLifecycle.VALIDATED,
        actor=board_manager_actor("board-1"),
        reason="validated for projection fixture",
    )

    vault = tmp_path / "vault"
    result = ImprovementMarkdownProjection().export(
        store,
        vault,
        generated_at=datetime(2026, 10, 31, 19, 0, tzinfo=UTC),
    )
    stem = improvement_markdown_stem(first_id)
    text = (vault / "blackboard" / "improvements" / f"{stem}.md").read_text(encoding="utf-8")

    assert "lifecycle: VALIDATED" in text
    assert "priority: HIGH" in text
    assert "[[skills/cursor-meta-epic-executor]]" in text
    assert "[[skills/origin]]" in text
    assert f"[[repositories/{repository_markdown_stem('jannekbuengener/agent-workforce')}]]" in text
    related_stem = improvement_markdown_stem(second_id)
    assert f"[[improvements/{related_stem}]]" in text
    assert "[[work/jannekbuengener--agent-workforce-issue-44|" in text
    assert "## Observations" in text
    assert "obs-a" in text
    assert "obs-a2" in text
    assert "evidence::obs-a" in text

    views = vault / "blackboard" / "views"
    assert (views / "by-lifecycle.md").is_file()
    assert (views / "by-priority.md").is_file()
    assert (views / "by-skill.md").is_file()
    assert (views / "by-repository.md").is_file()
    assert (views / "open.md").is_file()
    assert (views / "validated.md").is_file()
    assert (views / "verified.md").is_file()
    assert (vault / "blackboard" / "skills" / "cursor-meta-epic-executor.md").is_file()
    assert (
        vault
        / "blackboard"
        / "repositories"
        / f"{repository_markdown_stem('jannekbuengener/agent-workforce')}.md"
    ).is_file()
    meta = (vault / "blackboard" / "_projection" / "meta.json").read_text(encoding="utf-8")
    assert result.source_hash in meta
    assert PROJECTION_VERSION in meta


def test_rebuild_from_canonical_store_is_idempotent(tmp_path: Path) -> None:
    store = InMemoryImprovementObservationStore()
    _seed_ten(store)
    vault = tmp_path / "vault"
    generated_at = datetime(2026, 10, 31, 20, 0, tzinfo=UTC)
    projection = ImprovementMarkdownProjection()
    first = projection.export(store, vault, generated_at=generated_at)
    snapshot = {
        path.relative_to(vault).as_posix(): path.read_bytes()
        for path in vault.rglob("*")
        if path.is_file()
    }
    second = projection.export(store, vault, generated_at=generated_at)
    assert second.source_hash == first.source_hash
    assert second.skipped_manual_edits == ()
    rebuilt = {
        path.relative_to(vault).as_posix(): path.read_bytes()
        for path in vault.rglob("*")
        if path.is_file()
    }
    assert rebuilt == snapshot


def test_manual_edits_are_detected_and_not_silently_overwritten(tmp_path: Path) -> None:
    store = InMemoryImprovementObservationStore()
    improvement_id = store.submit_observation(
        _obs(
            "obs-1",
            skill_id="wrangler",
            root="binding-name-collision",
            key="k1",
        )
    ).improvement.improvement_id
    vault = tmp_path / "vault"
    generated_at = datetime(2026, 10, 31, 21, 0, tzinfo=UTC)
    projection = ImprovementMarkdownProjection()
    projection.export(store, vault, generated_at=generated_at)

    target = (
        vault
        / "blackboard"
        / "improvements"
        / f"{improvement_markdown_stem(improvement_id)}.md"
    )
    original = target.read_text(encoding="utf-8")
    target.write_text(original + "\n<!-- human note -->\n", encoding="utf-8")

    with pytest.raises(ImprovementProjectionConflict) as exc_info:
        projection.export(store, vault, generated_at=generated_at)
    assert improvement_markdown_stem(improvement_id) in str(exc_info.value)

    # Content must remain the human edit.
    assert "human note" in target.read_text(encoding="utf-8")

    forced = projection.export(store, vault, generated_at=generated_at, force=True)
    assert forced.skipped_manual_edits == ()
    assert "human note" not in target.read_text(encoding="utf-8")


def test_stable_stems_are_filesystem_safe() -> None:
    improvement_id = build_improvement_id(
        skill_id="cursor-meta-epic-executor",
        root_cause_key="host-visual-evidence-floor",
    )
    stem = improvement_markdown_stem(improvement_id)
    assert ":" not in stem
    assert "/" not in stem
    assert stem.startswith("IMP-")
    assert repository_markdown_stem("jannekbuengener/agent-workforce") == (
        "jannekbuengener--agent-workforce"
    )


def test_projection_does_not_touch_memory_or_knowledge_ports() -> None:
    source = Path(__file__).resolve().parents[2] / "src" / "agent_brain" / "improvement" / "projection.py"
    text = source.read_text(encoding="utf-8")
    assert "MemoryStore" not in text
    assert "KnowledgeStore" not in text
    assert "remember(" not in text
