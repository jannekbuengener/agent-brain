"""CLI entry for the capability-gated Improvement protocol (#50).

Usage:
  python -m agent_brain.improvement.cli capabilities --actor a --run r --cap improvement_read
  python -m agent_brain.improvement.cli schemas
  python -m agent_brain.improvement.cli invoke ...
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from agent_brain.contracts.serialization import serialize_contract
from agent_brain.improvement.protocol import (
    ImprovementCapability,
    ImprovementProtocolGateway,
    ProtocolCaller,
    capability_readback,
    result_to_dict,
    tool_schemas,
)


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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "schemas":
        print(serialize_contract(tool_schemas()))
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
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(serialize_contract({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 2
    print(serialize_contract(result_to_dict(result)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
