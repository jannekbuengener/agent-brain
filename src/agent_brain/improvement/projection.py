"""Read-only Markdown/Obsidian projection of the Improvement Blackboard (#51).

One-way Brain -> vault export. The vault is never a second mutable source of
truth and this module exposes no write-back / import API.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath

from agent_brain.contracts._validation import format_utc_datetime, normalize_utc_datetime
from agent_brain.contracts.improvement import (
    Improvement,
    ImprovementLifecycle,
    ImprovementObservation,
    ImprovementWorkRef,
    WorkRefKind,
)
from agent_brain.improvement.errors import ImprovementProjectionConflict
from agent_brain.improvement.ports import ImprovementObservationStore

PROJECTION_VERSION = "improvement-projection/v1"
_VAULT_ROOT_NAME = "blackboard"
_MANIFEST_REL = PurePosixPath("_projection/manifest.json")
_META_REL = PurePosixPath("_projection/meta.json")
_UNSAFE_STEM_RE = re.compile(r"[^a-zA-Z0-9._-]+")

_OPEN_LIFECYCLES = frozenset(
    {
        ImprovementLifecycle.NEW,
        ImprovementLifecycle.RECURRING,
        ImprovementLifecycle.VALIDATED,
        ImprovementLifecycle.PLANNED,
        ImprovementLifecycle.IMPLEMENTED,
    }
)


@dataclass(frozen=True, slots=True)
class ProjectionExportResult:
    """Outcome of a deterministic vault export."""

    vault_root: Path
    projection_version: str
    source_hash: str
    generated_at: datetime
    files_written: tuple[str, ...]
    skipped_manual_edits: tuple[str, ...]


def improvement_markdown_stem(improvement_id: str) -> str:
    """Stable filesystem-safe stem for an Improvement note."""
    raw = improvement_id.strip().removeprefix("improvement:")
    slug = raw.replace(":", "--").replace("/", "--")
    slug = _UNSAFE_STEM_RE.sub("-", slug).strip("-._")
    return f"IMP-{slug}"


def repository_markdown_stem(repository_ref: str) -> str:
    """Stable filesystem-safe stem for a repository index note."""
    slug = repository_ref.strip().replace("/", "--").replace(":", "--")
    return _UNSAFE_STEM_RE.sub("-", slug).strip("-._")


def skill_markdown_stem(skill_id: str) -> str:
    """Stable filesystem-safe stem for a skill index note."""
    slug = skill_id.strip().replace("/", "--").replace(":", "--")
    return _UNSAFE_STEM_RE.sub("-", slug).strip("-._")


def work_ref_markdown_stem(work_ref: ImprovementWorkRef) -> str:
    """Stable stem for a work-ref stub note."""
    kind = {
        WorkRefKind.GITHUB_ISSUE: "issue",
        WorkRefKind.GITHUB_PULL_REQUEST: "pr",
        WorkRefKind.VERIFICATION: "verification",
    }[work_ref.kind]
    repo = repository_markdown_stem(work_ref.repository_ref)
    ref = _UNSAFE_STEM_RE.sub("-", work_ref.ref.strip()).strip("-._")
    return f"{repo}-{kind}-{ref}"


def compute_source_hash(store: ImprovementObservationStore) -> str:
    """Hash canonical Improvement + Observation state for projection metadata."""
    improvements = sorted(
        store.list_improvements(),
        key=lambda item: item.improvement_id,
    )
    payload: dict[str, object] = {
        "improvements": [item.to_dict() for item in improvements],
        "observations": {},
    }
    observations_map: dict[str, list[dict[str, object]]] = {}
    for item in improvements:
        history = store.list_observations(item.improvement_id)
        observations_map[item.improvement_id] = [event.to_dict() for event in history]
    payload["observations"] = {
        key: observations_map[key] for key in sorted(observations_map)
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _yaml_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    text = str(value)
    if text == "":
        return '""'
    if re.fullmatch(r"[A-Za-z0-9_./:@+-]+", text):
        return text
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _render_frontmatter(fields: Mapping[str, object]) -> str:
    lines = ["---"]
    for key in fields:
        value = fields[key]
        if isinstance(value, (list, tuple)):
            if not value:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {_yaml_scalar(item)}")
        else:
            lines.append(f"{key}: {_yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ImprovementMarkdownProjection:
    """Deterministic one-way exporter: Agent Brain store -> Markdown vault."""

    # Explicitly absent write-back surface (asserted by tests).
    WRITE_BACK_METHODS = frozenset(
        {
            "import_from_vault",
            "import_vault",
            "apply_vault_edits",
            "write_back",
            "sync_from_markdown",
            "upsert_from_markdown",
            "merge_vault_into_store",
        }
    )

    def export(
        self,
        store: ImprovementObservationStore,
        vault_root: Path | str,
        *,
        generated_at: datetime | None = None,
        force: bool = False,
    ) -> ProjectionExportResult:
        """Export the full vault. Raises on manual edits unless ``force=True``."""
        if generated_at is None:
            raise ValueError("generated_at is required for deterministic exports")
        generated = normalize_utc_datetime(generated_at, "generated_at")
        root = Path(vault_root)
        board = root / _VAULT_ROOT_NAME
        source_hash = compute_source_hash(store)
        improvements = sorted(store.list_improvements(), key=lambda item: item.improvement_id)
        observations = {
            item.improvement_id: store.list_observations(item.improvement_id)
            for item in improvements
        }

        planned = self._plan_vault(
            improvements=improvements,
            observations=observations,
            source_hash=source_hash,
            generated_at=generated,
        )
        previous_manifest = self._load_manifest(board)
        conflicts: list[str] = []
        for rel, content in planned.items():
            path = board / Path(rel)
            if not path.is_file():
                continue
            existing = path.read_text(encoding="utf-8")
            if existing == content:
                continue
            previous_hash = previous_manifest.get(rel)
            if previous_hash is not None and previous_hash == _sha256_text(existing):
                continue
            conflicts.append(rel)

        if conflicts and not force:
            raise ImprovementProjectionConflict(
                "manual vault edits detected; refusing silent overwrite: "
                + ", ".join(sorted(conflicts))
            )

        written: list[str] = []
        for rel, content in sorted(planned.items()):
            path = board / Path(rel)
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.is_file() and path.read_text(encoding="utf-8") == content:
                continue
            path.write_text(content, encoding="utf-8", newline="\n")
            written.append(rel)

        # Prune stale projected files that still match the previous manifest.
        for rel, previous_hash in sorted(previous_manifest.items()):
            if rel in planned:
                continue
            path = board / Path(rel)
            if not path.is_file():
                continue
            existing = path.read_text(encoding="utf-8")
            if force or previous_hash == _sha256_text(existing):
                path.unlink()
                written.append(f"deleted:{rel}")

        manifest = {rel: _sha256_text(content) for rel, content in planned.items()}
        # Manifest is written last and included only as bookkeeping (not hashed into itself).
        manifest_path = board / Path(_MANIFEST_REL)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_body = json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
        if (not manifest_path.is_file()) or manifest_path.read_text(encoding="utf-8") != manifest_body:
            manifest_path.write_text(manifest_body, encoding="utf-8", newline="\n")
            written.append(_MANIFEST_REL.as_posix())

        return ProjectionExportResult(
            vault_root=root.resolve(),
            projection_version=PROJECTION_VERSION,
            source_hash=source_hash,
            generated_at=generated,
            files_written=tuple(written),
            skipped_manual_edits=(),
        )

    def _load_manifest(self, board: Path) -> dict[str, str]:
        path = board / Path(_MANIFEST_REL)
        if not path.is_file():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        if not isinstance(payload, dict):
            return {}
        return {
            str(key): str(value)
            for key, value in payload.items()
            if isinstance(key, str) and isinstance(value, str)
        }

    def _plan_vault(
        self,
        *,
        improvements: list[Improvement],
        observations: Mapping[str, tuple[ImprovementObservation, ...]],
        source_hash: str,
        generated_at: datetime,
    ) -> dict[str, str]:
        planned: dict[str, str] = {}
        generated_at_text = format_utc_datetime(generated_at)

        planned[_META_REL.as_posix()] = (
            json.dumps(
                {
                    "projection_version": PROJECTION_VERSION,
                    "source_hash": source_hash,
                    "generated_at": generated_at_text,
                    "improvement_count": len(improvements),
                    "read_only": True,
                    "direction": "brain_to_markdown",
                },
                sort_keys=True,
                indent=2,
                ensure_ascii=True,
            )
            + "\n"
        )

        skill_index: dict[str, list[Improvement]] = defaultdict(list)
        repo_index: dict[str, list[Improvement]] = defaultdict(list)
        lifecycle_index: dict[str, list[Improvement]] = defaultdict(list)
        priority_index: dict[str, list[Improvement]] = defaultdict(list)
        work_refs: dict[str, ImprovementWorkRef] = {}

        for item in improvements:
            stem = improvement_markdown_stem(item.improvement_id)
            planned[f"improvements/{stem}.md"] = self._render_improvement(
                item,
                observations=observations.get(item.improvement_id, ()),
                source_hash=source_hash,
                generated_at_text=generated_at_text,
            )
            skill_index[item.skill_id].append(item)
            for related_skill in item.related_skill_ids:
                skill_index[related_skill].append(item)
            for repo in item.repository_refs:
                repo_index[repo].append(item)
            lifecycle_index[item.lifecycle.value].append(item)
            priority_key = item.priority.value if item.priority is not None else "UNSET"
            priority_index[priority_key].append(item)
            for work_ref in item.work_refs:
                work_refs[work_ref_markdown_stem(work_ref)] = work_ref

        for skill_id, items in sorted(skill_index.items()):
            stem = skill_markdown_stem(skill_id)
            planned[f"skills/{stem}.md"] = self._render_skill_page(
                skill_id,
                items,
                source_hash=source_hash,
                generated_at_text=generated_at_text,
            )

        for repo, items in sorted(repo_index.items()):
            stem = repository_markdown_stem(repo)
            planned[f"repositories/{stem}.md"] = self._render_repository_page(
                repo,
                items,
                source_hash=source_hash,
                generated_at_text=generated_at_text,
            )

        for stem, work_ref in sorted(work_refs.items()):
            planned[f"work/{stem}.md"] = self._render_work_ref_page(
                work_ref,
                source_hash=source_hash,
                generated_at_text=generated_at_text,
            )

        planned["views/by-lifecycle.md"] = self._render_grouped_view(
            title="Improvements by lifecycle",
            groups={key: lifecycle_index[key] for key in sorted(lifecycle_index)},
            source_hash=source_hash,
            generated_at_text=generated_at_text,
        )
        planned["views/by-priority.md"] = self._render_grouped_view(
            title="Improvements by priority",
            groups={key: priority_index[key] for key in sorted(priority_index)},
            source_hash=source_hash,
            generated_at_text=generated_at_text,
        )
        planned["views/by-skill.md"] = self._render_grouped_view(
            title="Improvements by skill",
            groups={key: skill_index[key] for key in sorted(skill_index)},
            source_hash=source_hash,
            generated_at_text=generated_at_text,
        )
        planned["views/by-repository.md"] = self._render_grouped_view(
            title="Improvements by repository",
            groups={key: repo_index[key] for key in sorted(repo_index)},
            source_hash=source_hash,
            generated_at_text=generated_at_text,
        )
        planned["views/open.md"] = self._render_flat_view(
            title="Open improvements",
            items=[item for item in improvements if item.lifecycle in _OPEN_LIFECYCLES],
            source_hash=source_hash,
            generated_at_text=generated_at_text,
        )
        planned["views/validated.md"] = self._render_flat_view(
            title="Validated improvements",
            items=[
                item for item in improvements if item.lifecycle is ImprovementLifecycle.VALIDATED
            ],
            source_hash=source_hash,
            generated_at_text=generated_at_text,
        )
        planned["views/verified.md"] = self._render_flat_view(
            title="Verified improvements",
            items=[
                item for item in improvements if item.lifecycle is ImprovementLifecycle.VERIFIED
            ],
            source_hash=source_hash,
            generated_at_text=generated_at_text,
        )
        planned["index.md"] = self._render_index(
            improvements,
            source_hash=source_hash,
            generated_at_text=generated_at_text,
        )
        return planned

    def _render_improvement(
        self,
        item: Improvement,
        *,
        observations: tuple[ImprovementObservation, ...],
        source_hash: str,
        generated_at_text: str,
    ) -> str:
        fields: dict[str, object] = {
            "projection_version": PROJECTION_VERSION,
            "source_hash": source_hash,
            "generated_at": generated_at_text,
            "schema_version": item.schema_version,
            "improvement_id": item.improvement_id,
            "skill_id": item.skill_id,
            "root_cause_key": item.root_cause_key,
            "lifecycle": item.lifecycle.value,
            "priority": item.priority.value if item.priority is not None else None,
            "confidence": item.confidence,
            "recurrence": item.recurrence,
            "revision": item.revision,
            "first_seen": format_utc_datetime(item.first_seen),
            "last_seen": format_utc_datetime(item.last_seen),
            "repository_refs": list(item.repository_refs),
            "task_refs": list(item.task_refs),
            "related_skill_ids": list(item.related_skill_ids),
            "aliases": list(item.aliases),
            "superseded_by_improvement_id": item.superseded_by_improvement_id,
            "read_only_projection": True,
        }
        body: list[str] = [
            _render_frontmatter(fields),
            "",
            f"# {item.summary}",
            "",
            "## Recommendation",
            "",
            item.recommendation,
            "",
            "## Expected benefit",
            "",
            item.expected_benefit,
            "",
            "## Links",
            "",
            f"- Skill: [[skills/{skill_markdown_stem(item.skill_id)}]]",
        ]
        for skill_id in item.related_skill_ids:
            body.append(f"- Related skill: [[skills/{skill_markdown_stem(skill_id)}]]")
        for repo in item.repository_refs:
            body.append(f"- Repository: [[repositories/{repository_markdown_stem(repo)}]]")
        for relation in item.relations:
            related_stem = improvement_markdown_stem(relation.related_improvement_id)
            reason = f" ({relation.reason})" if relation.reason else ""
            body.append(
                f"- Related improvement ({relation.kind.value}): "
                f"[[improvements/{related_stem}]]{reason}"
            )
        for work_ref in item.work_refs:
            stem = work_ref_markdown_stem(work_ref)
            label = f"{work_ref.repository_ref} {work_ref.kind.value} {work_ref.ref}"
            body.append(f"- Work: [[work/{stem}|{label}]]")

        body.extend(["", "## Observations", ""])
        if not observations:
            body.append("_No observations._")
        else:
            for event in observations:
                body.extend(
                    [
                        f"### {event.observation_id} — {format_utc_datetime(event.timestamp)}",
                        "",
                        f"- agent_id: `{event.agent_id}`",
                        f"- run_id: `{event.run_id}`",
                        f"- idempotency_key: `{event.idempotency_key}`",
                    ]
                )
                if event.repository_ref is not None:
                    body.append(
                        f"- repository: "
                        f"[[repositories/{repository_markdown_stem(event.repository_ref)}]]"
                    )
                body.extend(
                    [
                        "",
                        event.observation,
                        "",
                        f"**Recommendation:** {event.recommendation}",
                        "",
                        "Evidence:",
                        "",
                    ]
                )
                for evidence in event.evidence:
                    body.append(f"- `{evidence}`")
                body.append("")

        if item.merge_lineage:
            body.extend(["## Merge lineage", ""])
            for lineage in item.merge_lineage:
                body.append(
                    f"- `{lineage.merge_id}` by `{lineage.actor_id}` at "
                    f"{format_utc_datetime(lineage.merged_at)}: {lineage.reason}"
                )
                for source_id in lineage.source_improvement_ids:
                    body.append(f"  - source: [[improvements/{improvement_markdown_stem(source_id)}]]")
            body.append("")

        body.append("")
        return "\n".join(body)

    def _common_frontmatter(self, *, source_hash: str, generated_at_text: str) -> dict[str, object]:
        return {
            "projection_version": PROJECTION_VERSION,
            "source_hash": source_hash,
            "generated_at": generated_at_text,
            "read_only_projection": True,
        }

    def _render_skill_page(
        self,
        skill_id: str,
        items: list[Improvement],
        *,
        source_hash: str,
        generated_at_text: str,
    ) -> str:
        unique = sorted({item.improvement_id: item for item in items}.values(), key=lambda i: i.improvement_id)
        lines = [
            _render_frontmatter(
                {
                    **self._common_frontmatter(
                        source_hash=source_hash, generated_at_text=generated_at_text
                    ),
                    "skill_id": skill_id,
                }
            ),
            "",
            f"# Skill `{skill_id}`",
            "",
            "## Improvements",
            "",
        ]
        for item in unique:
            stem = improvement_markdown_stem(item.improvement_id)
            lines.append(f"- [[improvements/{stem}]] — {item.lifecycle.value} — {item.summary}")
        lines.append("")
        return "\n".join(lines)

    def _render_repository_page(
        self,
        repository_ref: str,
        items: list[Improvement],
        *,
        source_hash: str,
        generated_at_text: str,
    ) -> str:
        unique = sorted({item.improvement_id: item for item in items}.values(), key=lambda i: i.improvement_id)
        lines = [
            _render_frontmatter(
                {
                    **self._common_frontmatter(
                        source_hash=source_hash, generated_at_text=generated_at_text
                    ),
                    "repository_ref": repository_ref,
                }
            ),
            "",
            f"# Repository `{repository_ref}`",
            "",
            "## Improvements",
            "",
        ]
        for item in unique:
            stem = improvement_markdown_stem(item.improvement_id)
            lines.append(f"- [[improvements/{stem}]] — {item.lifecycle.value} — {item.summary}")
        lines.append("")
        return "\n".join(lines)

    def _render_work_ref_page(
        self,
        work_ref: ImprovementWorkRef,
        *,
        source_hash: str,
        generated_at_text: str,
    ) -> str:
        lines = [
            _render_frontmatter(
                {
                    **self._common_frontmatter(
                        source_hash=source_hash, generated_at_text=generated_at_text
                    ),
                    "kind": work_ref.kind.value,
                    "repository_ref": work_ref.repository_ref,
                    "ref": work_ref.ref,
                    "url": work_ref.url,
                }
            ),
            "",
            f"# {work_ref.kind.value} `{work_ref.ref}`",
            "",
            f"- Repository: [[repositories/{repository_markdown_stem(work_ref.repository_ref)}]]",
        ]
        if work_ref.url:
            lines.append(f"- URL: {work_ref.url}")
        lines.append("")
        return "\n".join(lines)

    def _render_grouped_view(
        self,
        *,
        title: str,
        groups: Mapping[str, list[Improvement]],
        source_hash: str,
        generated_at_text: str,
    ) -> str:
        lines = [
            _render_frontmatter(
                self._common_frontmatter(
                    source_hash=source_hash, generated_at_text=generated_at_text
                )
            ),
            "",
            f"# {title}",
            "",
        ]
        for group_name, items in groups.items():
            lines.append(f"## {group_name}")
            lines.append("")
            unique = sorted(
                {item.improvement_id: item for item in items}.values(),
                key=lambda i: i.improvement_id,
            )
            if not unique:
                lines.append("_None._")
            else:
                for item in unique:
                    stem = improvement_markdown_stem(item.improvement_id)
                    lines.append(f"- [[improvements/{stem}]] — {item.summary}")
            lines.append("")
        return "\n".join(lines)

    def _render_flat_view(
        self,
        *,
        title: str,
        items: list[Improvement],
        source_hash: str,
        generated_at_text: str,
    ) -> str:
        lines = [
            _render_frontmatter(
                self._common_frontmatter(
                    source_hash=source_hash, generated_at_text=generated_at_text
                )
            ),
            "",
            f"# {title}",
            "",
        ]
        if not items:
            lines.append("_None._")
        else:
            for item in items:
                stem = improvement_markdown_stem(item.improvement_id)
                lines.append(
                    f"- [[improvements/{stem}]] — {item.lifecycle.value} — {item.summary}"
                )
        lines.append("")
        return "\n".join(lines)

    def _render_index(
        self,
        improvements: list[Improvement],
        *,
        source_hash: str,
        generated_at_text: str,
    ) -> str:
        lines = [
            _render_frontmatter(
                {
                    **self._common_frontmatter(
                        source_hash=source_hash, generated_at_text=generated_at_text
                    ),
                    "improvement_count": len(improvements),
                }
            ),
            "",
            "# Improvement Blackboard Projection",
            "",
            "Read-only Markdown projection of the Agent Brain Improvement Blackboard.",
            "Do not treat this vault as source of truth.",
            "",
            "## Views",
            "",
            "- [[views/open]]",
            "- [[views/validated]]",
            "- [[views/verified]]",
            "- [[views/by-lifecycle]]",
            "- [[views/by-priority]]",
            "- [[views/by-skill]]",
            "- [[views/by-repository]]",
            "",
            "## Improvements",
            "",
        ]
        for item in improvements:
            stem = improvement_markdown_stem(item.improvement_id)
            lines.append(f"- [[improvements/{stem}]] — {item.lifecycle.value} — {item.summary}")
        lines.append("")
        return "\n".join(lines)
