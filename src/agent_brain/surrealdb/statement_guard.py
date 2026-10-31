"""Product-neutral SurrealQL read-only statement guard (#10).

Extracted in spirit from Claire ``context_query`` classifier behaviour without
Claire trading-/governance table profiles. Fail-closed: unknown prefixes and
write/control verbs are denied.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


class WriteDeniedError(ValueError):
    """Raised when a statement is not an allowed read-only operation."""


DENIED_KEYWORDS = frozenset(
    {
        "CREATE",
        "INSERT",
        "UPDATE",
        "UPSERT",
        "DELETE",
        "RELATE",
        "MERGE",
        "PATCH",
        "DEFINE",
        "REMOVE",
        "ALTER",
        "LIVE",
        "KILL",
        "USE",
        "BEGIN",
        "COMMIT",
        "CANCEL",
        "EXPLAIN",
        "SHOW CHANGES",
        "INFO FOR ROOT",
        "APPLY",
        "MIGRATION",
        "TRANSACTION",
        "IMPORT",
        "EXPORT",
    }
)

ALLOWED_PREFIXES = ("SELECT", "INFO FOR DB", "INFO FOR TABLE", "INFO FOR NS")


@dataclass(frozen=True, slots=True)
class StatementClassification:
    statement: str
    normalized: str
    allowed: bool
    operation: str
    reason: str


def _normalize_statement(statement: str) -> str:
    collapsed = re.sub(r"\s+", " ", statement.strip())
    return collapsed.upper()


def classify_readonly_statement(statement: str) -> StatementClassification:
    """Classify a SurrealQL statement as allowed read-only or raise."""
    if not isinstance(statement, str) or not statement.strip():
        raise ValueError("statement must be a non-blank string")
    if ";" in statement:
        raise WriteDeniedError("multi-statement input is denied")

    normalized = _normalize_statement(statement)
    for keyword in sorted(DENIED_KEYWORDS, key=len, reverse=True):
        if normalized == keyword or normalized.startswith(f"{keyword} "):
            raise WriteDeniedError(f"{keyword} statements are denied")

    for prefix in ALLOWED_PREFIXES:
        if normalized == prefix or normalized.startswith(f"{prefix} "):
            return StatementClassification(
                statement=statement,
                normalized=normalized,
                allowed=True,
                operation=prefix,
                reason="read-only statement allowed",
            )

    raise WriteDeniedError("statement is not in the read-only allowlist")
