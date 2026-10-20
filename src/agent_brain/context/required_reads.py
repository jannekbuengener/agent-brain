"""Product-neutral required-reads profile and deterministic resolver."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
_DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def _text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{field_name} must be a tuple or list of strings")
    return tuple(_required_text(item, field_name) for item in values)


def _priority(value: str) -> str:
    normalized = _required_text(value, "priority").lower()
    if normalized not in _PRIORITY_RANK:
        raise ValueError(f"unsupported priority: {value!r}")
    return normalized


def _is_safe_relative_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.startswith(("/", "//")) or _DRIVE_PATH_RE.match(path):
        return False
    return all(segment != ".." for segment in normalized.split("/"))


@dataclass(frozen=True, slots=True)
class RequiredRead:
    path: str
    priority: str
    reason: str
    source_ref: str | None = None
    available: bool = False
    warning: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _required_text(self.path, "path"))
        object.__setattr__(self, "priority", _priority(self.priority))
        object.__setattr__(self, "reason", _required_text(self.reason, "reason"))
        if self.source_ref is not None:
            object.__setattr__(self, "source_ref", _required_text(self.source_ref, "source_ref"))
        if not isinstance(self.available, bool):
            raise TypeError("available must be a bool")
        if self.warning is not None:
            object.__setattr__(self, "warning", _required_text(self.warning, "warning"))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "path": self.path,
            "priority": self.priority,
            "reason": self.reason,
            "available": self.available,
        }
        if self.source_ref is not None:
            payload["source_ref"] = self.source_ref
        if self.warning is not None:
            payload["warning"] = self.warning
        return payload


@dataclass(frozen=True, slots=True)
class RequiredReadRule:
    path: str
    priority: str
    reason: str
    source_ref: str | None = None
    keywords: tuple[str, ...] = ()
    operation_modes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _required_text(self.path, "path"))
        object.__setattr__(self, "priority", _priority(self.priority))
        object.__setattr__(self, "reason", _required_text(self.reason, "reason"))
        if self.source_ref is not None:
            object.__setattr__(self, "source_ref", _required_text(self.source_ref, "source_ref"))
        object.__setattr__(self, "keywords", _text_tuple(self.keywords, "keywords"))
        object.__setattr__(
            self,
            "operation_modes",
            tuple(item.lower() for item in _text_tuple(self.operation_modes, "operation_modes")),
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RequiredReadRule:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dict")
        return cls(
            path=payload.get("path", ""),
            priority=payload.get("priority", ""),
            reason=payload.get("reason", ""),
            source_ref=payload.get("source_ref"),
            keywords=payload.get("keywords", ()),
            operation_modes=payload.get("operation_modes", ()),
        )


@dataclass(frozen=True, slots=True)
class RequiredReadsProfile:
    minimum: tuple[RequiredReadRule, ...]
    conditional: tuple[RequiredReadRule, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.minimum, (tuple, list)) or not isinstance(
            self.conditional, (tuple, list)
        ):
            raise TypeError("minimum and conditional must be tuples or lists")
        for item in (*self.minimum, *self.conditional):
            if not isinstance(item, RequiredReadRule):
                raise TypeError("profile entries must be RequiredReadRule values")
        object.__setattr__(self, "minimum", tuple(self.minimum))
        object.__setattr__(self, "conditional", tuple(self.conditional))


def _matches(rule: RequiredReadRule, *, haystack: str, operation_mode: str) -> bool:
    keyword_match = not rule.keywords or any(
        keyword.casefold() in haystack for keyword in rule.keywords
    )
    mode_match = not rule.operation_modes or operation_mode.casefold() in rule.operation_modes
    return keyword_match and mode_match


def resolve_required_reads(
    *,
    profile: RequiredReadsProfile,
    task_scope: str,
    operation_mode: str,
    target_issue: str | None = None,
    target_paths: tuple[str, ...] = (),
    target_symbols: tuple[str, ...] = (),
    target_concepts: tuple[str, ...] = (),
    available_paths: frozenset[str] | None = None,
) -> tuple[RequiredRead, ...]:
    """Resolve required reads without filesystem access or built-in product catalogs."""
    if not isinstance(profile, RequiredReadsProfile):
        raise TypeError("profile must be a RequiredReadsProfile")
    scope = _required_text(task_scope, "task_scope")
    mode = _required_text(operation_mode, "operation_mode").lower()
    issue = _required_text(target_issue, "target_issue") if target_issue is not None else ""
    paths = _text_tuple(target_paths, "target_paths")
    symbols = _text_tuple(target_symbols, "target_symbols")
    concepts = _text_tuple(target_concepts, "target_concepts")
    haystack = " ".join((scope, issue, *paths, *symbols, *concepts)).casefold()

    selected = list(profile.minimum)
    selected.extend(
        rule for rule in profile.conditional if _matches(rule, haystack=haystack, operation_mode=mode)
    )

    by_path: dict[str, RequiredReadRule] = {}
    order: dict[str, int] = {}
    for index, rule in enumerate(selected):
        incumbent = by_path.get(rule.path)
        if incumbent is None:
            by_path[rule.path] = rule
            order[rule.path] = index
        elif _PRIORITY_RANK[rule.priority] < _PRIORITY_RANK[incumbent.priority]:
            by_path[rule.path] = rule

    reads: list[RequiredRead] = []
    for rule in by_path.values():
        safe = _is_safe_relative_path(rule.path)
        if not safe:
            available = False
            warning = "unsafe_path"
        elif available_paths is None:
            available = False
            warning = "availability_not_provided"
        elif rule.path in available_paths:
            available = True
            warning = None
        else:
            available = False
            warning = "not_available"
        reads.append(
            RequiredRead(
                path=rule.path,
                priority=rule.priority,
                reason=rule.reason,
                source_ref=rule.source_ref,
                available=available,
                warning=warning,
            )
        )

    return tuple(
        sorted(
            reads,
            key=lambda item: (_PRIORITY_RANK[item.priority], order[item.path]),
        )
    )
