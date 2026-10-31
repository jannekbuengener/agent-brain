"""CLI entry for the capability-gated Improvement protocol (#50).

Usage:
  python -m agent_brain.improvement.cli capabilities --actor a --run r --cap improvement_read
  python -m agent_brain.improvement.cli schemas
  python -m agent_brain.improvement.cli invoke ...
  python -m agent_brain.improvement.cli export-projection --db PATH --vault PATH --generated-at ISO8601
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from agent_brain.contracts._validation import parse_utc_datetime
from agent_brain.contracts.serialization import serialize_contract
from agent_brain.improvement.projection import ImprovementMarkdownProjection
from agent_brain.improvement.protocol import (
    ImprovementCapability,
    ImprovementProtocolGateway,
    ProtocolCaller,
    capability_readback,
    result_to_dict,
    tool_schemas,
)
from agent_brain.improvement.sqlite import SqliteImprovementObservationStore


def _parse_caps(raw: Sequence[str]) -> frozenset[ImprovementCapability]:
    return frozenset(ImprovementCapability(item) for item in raw)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-brain-improvement")
    sub = parser.add_subparsers(dest="command", required=True)

    schemas = sub.add_parser("schemas", help="Print host-neutral tool schemas")
    _ = schemas

    caps = sub.add_parser("capabilities", help="Capability readback for a caller")
    caps.add_argument("--actor", required=True)
    caps.add_argument("--run", required=True)
    caps.add_argument(
        "--cap",
        action="append",
        default=[],
        dest="caps",
        help="Granted capability id (repeatable)",
    )

    invoke = sub.add_parser("invoke", help="Invoke one protocol tool with JSON payload")
    invoke.add_argument("--actor", required=True)
    invoke.add_argument("--run", required=True)
    invoke.add_argument(
        "--cap",
        action="append",
        default=[],
        dest="caps",
        help="Granted capability id (repeatable)",
    )
    invoke.add_argument("--tool", required=True)
    invoke.add_argument(
        "--payload",
        default="{}",
        help="JSON object of tool arguments",
    )

    export = sub.add_parser(
        "export-projection",
        help="Deterministic read-only Markdown/Obsidian vault export from SQLite store",
    )
    export.add_argument("--db", required=True, help="Path to Improvement SQLite database")
    export.add_argument("--vault", required=True, help="Vault root directory to write")
    export.add_argument(
        "--generated-at",
        required=True,
        help="UTC timestamp (ISO-8601) baked into projection metadata",
    )
    export.add_argument(
        "--force",
        action="store_true",
        help="Overwrite vault files even when manual edits are detected",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "schemas":
        print(serialize_contract(tool_schemas()))
        return 0

    if args.command == "export-projection":
        generated_at = parse_utc_datetime(args.generated_at, "generated_at")
        store = SqliteImprovementObservationStore(Path(args.db))
        result = ImprovementMarkdownProjection().export(
            store,
            Path(args.vault),
            generated_at=generated_at,
            force=bool(args.force),
        )
        print(
            serialize_contract(
                {
                    "projection_version": result.projection_version,
                    "source_hash": result.source_hash,
                    "generated_at": result.generated_at.isoformat().replace("+00:00", "Z")
                    if isinstance(result.generated_at, datetime)
                    else str(result.generated_at),
                    "files_written": list(result.files_written),
                    "skipped_manual_edits": list(result.skipped_manual_edits),
                    "vault_root": str(result.vault_root),
                }
            )
        )
        return 0

    caller = ProtocolCaller(
        actor_id=args.actor,
        run_id=args.run,
        capabilities=_parse_caps(args.caps),
    )
    if args.command == "capabilities":
        print(serialize_contract(capability_readback(caller)))
        return 0

    gateway = ImprovementProtocolGateway()
    payload = json.loads(args.payload)
    if not isinstance(payload, dict):
        raise SystemExit("payload must be a JSON object")
    try:
        result = gateway.invoke(caller, args.tool, **payload)
    except Exception as exc:
        print(serialize_contract({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 2
    print(serialize_contract(result_to_dict(result)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
