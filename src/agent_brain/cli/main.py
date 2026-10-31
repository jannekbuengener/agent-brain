"""agent-brain CLI entrypoint — transport only (#12)."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from agent_brain.contracts.serialization import serialize_contract
from agent_brain.protocol import (
    EXIT_SUCCESS,
    ProtocolErrorCode,
    ProtocolGateway,
    ProtocolRequest,
    exit_code_for,
    invoke,
)
from agent_brain.protocol.runtime import ProtocolRuntime, default_runtime


class _CliInputError(ValueError):
    """User-facing CLI input problem mapped to structured exit codes."""


def _load_payload(raw: str | None, path: str | None) -> dict[str, Any]:
    if raw and path:
        raise _CliInputError("use either --payload or --payload-file, not both")
    if path:
        text = Path(path).read_text(encoding="utf-8")
        data = json.loads(text)
    elif raw:
        data = json.loads(raw)
    else:
        return {}
    if not isinstance(data, Mapping):
        raise _CliInputError("payload must be a JSON object")
    return dict(data)


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON (default for invoke; optional for others)",
    )
    parser = argparse.ArgumentParser(
        prog="agent-brain",
        description=(
            "Standalone read-only Agent Brain CLI. "
            "Uses the shared protocol surface; independent of host apps and private MCP."
        ),
        parents=[common],
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("version", parents=[common], help="Show package / protocol version metadata")
    sub.add_parser("health", parents=[common], help="Show core and backend health")
    sub.add_parser("capabilities", parents=[common], help="Show available read-only capabilities")

    invoke_p = sub.add_parser("invoke", parents=[common], help="Invoke one protocol operation")
    invoke_p.add_argument("--operation", required=True)
    invoke_p.add_argument("--payload", default=None, help="JSON object payload")
    invoke_p.add_argument("--payload-file", default=None, help="Path to JSON payload")
    invoke_p.add_argument("--request-id", default=None)

    for name, help_text in (
        ("context", "context_read operation"),
        ("retrieval", "retrieval operation"),
        ("evidence", "evidence / trust operation"),
        ("memory-read", "memory_read operation"),
        ("surreal-read", "surreal_read capability gate"),
    ):
        cmd = sub.add_parser(name, parents=[common], help=help_text)
        cmd.add_argument("--payload", default=None)
        cmd.add_argument("--payload-file", default=None)
        cmd.add_argument("--request-id", default=None)

    return parser


_COMMAND_TO_OPERATION = {
    "version": "version",
    "health": "health",
    "capabilities": "capabilities",
    "context": "context_read",
    "retrieval": "retrieval",
    "evidence": "evidence",
    "memory-read": "memory_read",
    "surreal-read": "surreal_read",
}


def _print_human(operation: str, response_dict: Mapping[str, Any]) -> None:
    if not response_dict.get("ok"):
        error = response_dict.get("error") or {}
        code = error.get("code", "internal_failure")
        message = error.get("message", "unknown error")
        print(f"error [{code}]: {message}", file=sys.stderr)
        return
    data = response_dict.get("data") or {}
    if operation == "version":
        print(f"agent-brain {data.get('agent_brain_version', '?')}")
        print(f"protocol {data.get('protocol_schema', '?')}")
        tag = data.get("git_tag")
        if tag:
            print(f"tag {tag}")
        return
    if operation == "health":
        print(f"overall: {data.get('overall')}")
        for component in data.get("components") or ():
            detail = component.get("detail")
            suffix = f" ({detail})" if detail else ""
            print(f"- {component.get('name')}: {component.get('state')}{suffix}")
        return
    if operation == "capabilities":
        print(f"read_only: {data.get('read_only', True)}")
        for item in data.get("capabilities") or ():
            detail = item.get("detail")
            suffix = f" — {detail}" if detail else ""
            print(f"- {item.get('capability')}: {item.get('state')}{suffix}")
        return
    print(serialize_contract(dict(response_dict)))


def main(
    argv: Sequence[str] | None = None,
    *,
    runtime: ProtocolRuntime | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    bound_runtime = runtime if runtime is not None else default_runtime()
    as_json = bool(args.json) or args.command == "invoke"

    try:
        if args.command == "invoke":
            operation = args.operation
            payload = _load_payload(args.payload, args.payload_file)
            request_id = args.request_id
        else:
            operation = _COMMAND_TO_OPERATION[args.command]
            if args.command in {"version", "health", "capabilities"}:
                payload = {}
                request_id = None
            else:
                payload = _load_payload(args.payload, args.payload_file)
                request_id = args.request_id
    except json.JSONDecodeError as exc:
        print(f"error [invalid_input]: invalid JSON payload: {exc}", file=sys.stderr)
        return exit_code_for(ProtocolErrorCode.INVALID_INPUT)
    except _CliInputError as exc:
        print(f"error [invalid_input]: {exc}", file=sys.stderr)
        return exit_code_for(ProtocolErrorCode.INVALID_INPUT)

    response = ProtocolGateway(runtime=bound_runtime).invoke_sync(
        ProtocolRequest(operation=operation, payload=payload, request_id=request_id)
    )
    payload_out = response.to_dict()
    if as_json:
        print(serialize_contract(payload_out))
    else:
        _print_human(operation, payload_out)

    if response.ok:
        return EXIT_SUCCESS
    assert response.error is not None
    return exit_code_for(response.error.code)


def run() -> None:
    raise SystemExit(main())


# Re-export invoke for tests that want protocol parity without argparse.
__all__ = [
    "build_parser",
    "invoke",
    "main",
    "run",
]
