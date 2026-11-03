"""Local, explicit Agent Brain cross-agent work-handoff CLI.

No default writes, no raw SQL, no MCP auto-mutation, and no external LLM.
Write text is accepted from a JSON file or stdin rather than shell arguments.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from agent_brain.memory.handoff import (
    HandoffConflict,
    HandoffUnavailable,
    SurrealHandoffJournal,
    load_local_authorization,
)
from agent_brain.surrealdb.config import SurrealDbReadSettings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-brain-handoff")
    parser.add_argument(
        "--endpoint", default="http://127.0.0.1:8012", help="Local Agent Brain SurrealDB endpoint"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser(
        "write", help="Append an idempotent work handoff from a JSON file or stdin"
    )
    write.add_argument("--payload-file", required=True, help="JSON file or '-' for stdin")
    read = sub.add_parser("read", help="Recall handoffs for one explicitly named repository")
    read.add_argument("--repo", required=True, help="Exact owner/repo")
    read.add_argument("--task", default=None, help="Optional exact task/issue reference")
    read.add_argument("--limit", type=int, default=20)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.endpoint not in {"http://127.0.0.1:8012", "http://localhost:8012"}:
            raise ValueError("operator CLI is intentionally restricted to localhost:8012")
        # This first local single-operator slice does not expose DB credentials
        # to remote agents or claim true multi-tenant authorization.
        journal = SurrealHandoffJournal(
            SurrealDbReadSettings(
                endpoint=args.endpoint,
                namespace="agent_brain",
                database="shared_memory",
                expected_server_version_prefix="surrealdb-3.0",
                timeout_seconds=5.0,
            ),
            authorization=load_local_authorization(),
            initialize=args.command == "write",
        )
        if args.command == "write":
            raw = (
                sys.stdin.read()
                if args.payload_file == "-"
                else Path(args.payload_file).read_text(encoding="utf-8")
            )
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("payload must be a JSON object")
            if set(payload) != {
                "repository_ref",
                "agent_id",
                "task_ref",
                "status",
                "summary",
                "next_step",
                "source_ref",
                "idempotency_key",
            }:
                raise ValueError("payload has missing or unexpected fields")
            event = journal.append(**payload)
            print(json.dumps({"ok": True, "event": event.to_dict()}, ensure_ascii=False))
        else:
            events = journal.recall(repository_ref=args.repo, task_ref=args.task, limit=args.limit)
            print(
                json.dumps(
                    {"ok": True, "count": len(events), "events": [e.to_dict() for e in events]},
                    ensure_ascii=False,
                )
            )
        return 0
    except (OSError, TypeError, ValueError, HandoffUnavailable, HandoffConflict) as exc:
        # Backend errors intentionally redact credentials/SQL.
        message = str(exc)
        if isinstance(exc, HandoffUnavailable):
            message = "Agent Brain handoff database/auth unavailable"
        print(json.dumps({"ok": False, "error": message}, ensure_ascii=False), file=sys.stderr)
        return 1


def run() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    run()
