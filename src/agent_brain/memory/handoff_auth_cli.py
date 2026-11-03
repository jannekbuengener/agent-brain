"""Operator CLI for handoff consumer enroll / rotate / revoke / list.

Plaintext tokens are printed once on enroll/rotate only. Grant listings never
include token hashes. Requires AGENT_BRAIN_SECRETS_PATH.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from agent_brain.memory.handoff_auth import (
    HandoffAuthUnavailable,
    HandoffCredentialStore,
    HandoffForbidden,
    HandoffOperation,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-brain-handoff-auth")
    sub = parser.add_subparsers(dest="command", required=True)

    enroll = sub.add_parser("enroll", help="Create a least-privilege consumer grant")
    enroll.add_argument("--consumer-id", required=True)
    enroll.add_argument("--repository", required=True, help="Exact owner/repo")
    enroll.add_argument(
        "--ops",
        default="append,recall",
        help="Comma-separated operations: append,recall",
    )

    rotate = sub.add_parser("rotate", help="Revoke current token hash and mint a replacement")
    rotate.add_argument("--grant-id", required=True)

    revoke = sub.add_parser("revoke", help="Revoke grant; hash enters durable denylist")
    revoke.add_argument("--grant-id", required=True)
    revoke.add_argument("--reason", default="revoked")

    sub.add_parser("list", help="List grants without token hashes")
    return parser


def _ops(raw: str) -> list[HandoffOperation]:
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    return [HandoffOperation(part) for part in parts]


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        store = HandoffCredentialStore.for_secrets_dir()
        if args.command == "enroll":
            grant, token = store.enroll(
                consumer_id=args.consumer_id,
                repository_ref=args.repository,
                operations=_ops(args.ops),
            )
            print(
                json.dumps(
                    {
                        "ok": True,
                        "grant": grant.to_public_dict(),
                        "token": token,
                        "warning": "Store token outside git; it will not be shown again",
                    },
                    ensure_ascii=False,
                )
            )
        elif args.command == "rotate":
            grant, token = store.rotate(args.grant_id)
            print(
                json.dumps(
                    {
                        "ok": True,
                        "grant": grant.to_public_dict(),
                        "token": token,
                        "warning": "Previous token is revoked via denylist",
                    },
                    ensure_ascii=False,
                )
            )
        elif args.command == "revoke":
            grant = store.revoke(args.grant_id, reason=args.reason)
            print(json.dumps({"ok": True, "grant": grant.to_public_dict()}, ensure_ascii=False))
        else:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "grants": [grant.to_public_dict() for grant in store.list_grants()],
                    },
                    ensure_ascii=False,
                )
            )
        return 0
    except (OSError, TypeError, ValueError, HandoffForbidden, HandoffAuthUnavailable) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


def run() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    run()
