"""Thin Streamable HTTP MCP transport over the shared capability surface (#73 Goal 3).

Reuses ``McpStdioServer.handle_message`` / ``CapabilityMcpTransport``. No capability,
retrieval, evidence, or required-reads logic lives here. No MCP SDK dependency.
"""

from __future__ import annotations

import argparse
import json
import logging
import secrets
import threading
import time
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from agent_brain import __version__
from agent_brain.mcp.server import (
    MCP_PROTOCOL_VERSION,
    MCP_SERVER_NAME,
    McpStdioServer,
)
from agent_brain.mcp.transport import CapabilityMcpTransport

MCP_HTTP_SCHEMA = "agent-brain-mcp-streamable-http/v1"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
DEFAULT_PATH = "/mcp"
_SUPPORTED_PROTOCOL_VERSIONS = frozenset(
    {
        "2024-11-05",
        "2025-03-26",
        MCP_PROTOCOL_VERSION,
    }
)

_LOG = logging.getLogger("agent_brain.mcp.http")


class McpHttpSessionStore:
    """In-memory session table for Streamable HTTP ``Mcp-Session-Id``."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, float] = {}

    def create(self) -> str:
        session_id = secrets.token_urlsafe(24)
        with self._lock:
            self._sessions[session_id] = time.monotonic()
        return session_id

    def touch(self, session_id: str) -> bool:
        with self._lock:
            if session_id not in self._sessions:
                return False
            self._sessions[session_id] = time.monotonic()
            return True

    def discard(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)


class McpHttpServerState:
    """Shared process state for the HTTP MCP endpoint."""

    def __init__(
        self,
        *,
        transport: CapabilityMcpTransport | None = None,
        mcp_path: str = DEFAULT_PATH,
        allowed_origins: tuple[str, ...] | None = None,
    ) -> None:
        self.transport = transport if transport is not None else CapabilityMcpTransport()
        self.mcp = McpStdioServer(transport=self.transport)
        self.sessions = McpHttpSessionStore()
        self.mcp_path = mcp_path if mcp_path.startswith("/") else f"/{mcp_path}"
        self.allowed_origins = allowed_origins
        self.started_at = time.time()


def _negotiate_protocol_version(requested: object) -> str:
    if isinstance(requested, str) and requested in _SUPPORTED_PROTOCOL_VERSIONS:
        return requested
    return MCP_PROTOCOL_VERSION


def _json_bytes(payload: Mapping[str, object] | list[object]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _sse_bytes(payload: Mapping[str, object]) -> bytes:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: message\ndata: {data}\n\n".encode()


def _has_request(message: Mapping[str, Any] | list[Any]) -> bool:
    if isinstance(message, list):
        return any(
            isinstance(item, Mapping) and "method" in item and "id" in item for item in message
        )
    return "method" in message and "id" in message


class McpHttpRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler bound to a ``McpHttpServerState`` via server attribute."""

    server: ThreadingHTTPServer  # type: narrowed by create_http_server
    protocol_version = "HTTP/1.1"

    @property
    def state(self) -> McpHttpServerState:
        return self.server.agent_brain_state  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: object) -> None:
        # Bound operational logging only — never log bodies/secrets.
        _LOG.info(
            "http method=%s path=%s status_arg=%s",
            self.command,
            self.path,
            args[1] if len(args) > 1 else args[0] if args else "-",
        )

    def _origin_ok(self) -> bool:
        allowed = self.state.allowed_origins
        if allowed is None:
            return True
        origin = self.headers.get("Origin")
        if origin is None:
            # Non-browser clients (Inspector, tunnel-client) may omit Origin.
            return True
        return origin in allowed

    def _send(
        self,
        status: int,
        body: bytes,
        *,
        content_type: str,
        session_id: str | None = None,
        extra_headers: Mapping[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if session_id is not None:
            self.send_header("Mcp-Session-Id", session_id)
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _reject(self, status: int, message: str) -> None:
        payload = {"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": message}}
        self._send(status, _json_bytes(payload), content_type="application/json")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/healthz", "/health"}:
            body = _json_bytes(
                {
                    "ok": True,
                    "server": MCP_SERVER_NAME,
                    "version": __version__,
                    "schema": MCP_HTTP_SCHEMA,
                    "mcp_path": self.state.mcp_path,
                    "uptime_seconds": round(time.time() - self.state.started_at, 3),
                }
            )
            self._send(200, body, content_type="application/json")
            return
        if parsed.path != self.state.mcp_path:
            self._reject(404, "not found")
            return
        if not self._origin_ok():
            self._reject(403, "origin not allowed")
            return
        accept = self.headers.get("Accept", "")
        if "text/event-stream" not in accept:
            self.send_response(405)
            self.send_header("Allow", "POST, DELETE")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        # Idle SSE listen is optional; this surface is request/response oriented.
        self.send_response(405)
        self.send_header("Allow", "POST, DELETE")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != self.state.mcp_path:
            self._reject(404, "not found")
            return
        session_id = self.headers.get("Mcp-Session-Id")
        if not session_id:
            self._reject(400, "Mcp-Session-Id required to terminate session")
            return
        self.state.sessions.discard(session_id)
        self._send(204, b"", content_type="application/json")

    def do_POST(self) -> None:
        started = time.perf_counter()
        parsed = urlparse(self.path)
        if parsed.path != self.state.mcp_path:
            self._reject(404, "not found")
            return
        if not self._origin_ok():
            self._reject(403, "origin not allowed")
            return

        length_raw = self.headers.get("Content-Length", "0")
        try:
            length = int(length_raw)
        except ValueError:
            self._reject(400, "invalid Content-Length")
            return
        if length < 0 or length > 10_485_760:
            self._reject(400, "request body too large or invalid")
            return

        raw = self.rfile.read(length) if length else b""
        try:
            message = json.loads(raw.decode("utf-8") if raw else "null")
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._reject(400, "malformed JSON body")
            _LOG.warning(
                "transport failure class=malformed_request path=%s latency_ms=%.1f",
                self.state.mcp_path,
                (time.perf_counter() - started) * 1000,
            )
            return

        if not isinstance(message, (dict, list)):
            self._reject(400, "JSON-RPC body must be object or batch array")
            return

        session_header = self.headers.get("Mcp-Session-Id")
        is_initialize = (
            isinstance(message, dict)
            and message.get("method") == "initialize"
            and "id" in message
        )
        if session_header and not self.state.sessions.touch(session_header):
            self._reject(404, "unknown or expired MCP session")
            return
        if not is_initialize and session_header is None and _has_request(message):
            # Session is optional for first initialize; subsequent requests may omit
            # when clients treat the server as stateless. Accept either mode.
            pass

        if not _has_request(message):
            # Notifications / responses → 202
            if isinstance(message, dict):
                self.state.mcp.handle_message(message)
            elif isinstance(message, list):
                for item in message:
                    if isinstance(item, Mapping):
                        self.state.mcp.handle_message(item)
            self.send_response(202)
            self.send_header("Content-Length", "0")
            if session_header:
                self.send_header("Mcp-Session-Id", session_header)
            self.end_headers()
            return

        accept = self.headers.get("Accept", "application/json")
        prefer_sse = "text/event-stream" in accept and "application/json" not in accept

        session_id = session_header
        response_payload: dict[str, object] | list[object]
        tool_name: str | None = None

        if isinstance(message, list):
            batch: list[object] = []
            for item in message:
                if not isinstance(item, Mapping):
                    continue
                if item.get("method") == "tools/call":
                    params = item.get("params")
                    if isinstance(params, Mapping):
                        name = params.get("name")
                        if isinstance(name, str):
                            tool_name = name
                handled = self._handle_one(item)
                if handled is not None:
                    batch.append(handled)
            response_payload = batch
        else:
            if message.get("method") == "tools/call":
                params = message.get("params")
                if isinstance(params, Mapping):
                    name = params.get("name")
                    if isinstance(name, str):
                        tool_name = name
            if is_initialize:
                session_id = self.state.sessions.create()
                # Negotiate protocol version without forking capability semantics.
                params = message.get("params")
                requested = None
                if isinstance(params, Mapping):
                    requested = params.get("protocolVersion")
                negotiated = _negotiate_protocol_version(requested)
                handled = self.state.mcp.handle_message(message)
                assert handled is not None
                result = handled.get("result")
                if isinstance(result, dict):
                    result = dict(result)
                    result["protocolVersion"] = negotiated
                    meta = result.get("_meta")
                    if isinstance(meta, dict):
                        meta = dict(meta)
                        meta["agent_brain_mcp_http_schema"] = MCP_HTTP_SCHEMA
                        meta["transport"] = "streamable_http"
                        result["_meta"] = meta
                    handled = {
                        "jsonrpc": handled["jsonrpc"],
                        "id": handled["id"],
                        "result": result,
                    }
                response_payload = handled
            else:
                handled = self._handle_one(message)
                response_payload = handled if handled is not None else {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "error": {"code": -32603, "message": "internal failure"},
                }

        latency_ms = (time.perf_counter() - started) * 1000
        status_class = "ok"
        if isinstance(response_payload, dict) and "error" in response_payload:
            status_class = "rpc_error"
        elif (
            isinstance(response_payload, dict)
            and isinstance(response_payload.get("result"), Mapping)
            and response_payload["result"].get("isError") is True
        ):
            status_class = "tool_error"

        _LOG.info(
            "mcp tool=%s status=%s version=%s latency_ms=%.1f",
            tool_name or message.get("method") if isinstance(message, dict) else "batch",
            status_class,
            __version__,
            latency_ms,
        )

        if prefer_sse and isinstance(response_payload, dict):
            self._send(
                200,
                _sse_bytes(response_payload),
                content_type="text/event-stream",
                session_id=session_id,
            )
            return

        body = _json_bytes(response_payload)  # type: ignore[arg-type]
        self._send(
            200,
            body,
            content_type="application/json",
            session_id=session_id,
        )

    def _handle_one(self, message: Mapping[str, Any]) -> dict[str, object] | None:
        return self.state.mcp.handle_message(message)


def create_http_server(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    mcp_path: str = DEFAULT_PATH,
    transport: CapabilityMcpTransport | None = None,
    allowed_origins: tuple[str, ...] | None = None,
) -> ThreadingHTTPServer:
    """Create a bound ThreadingHTTPServer exposing Streamable HTTP MCP."""
    state = McpHttpServerState(
        transport=transport,
        mcp_path=mcp_path,
        allowed_origins=allowed_origins,
    )
    server = ThreadingHTTPServer((host, port), McpHttpRequestHandler)
    server.agent_brain_state = state  # type: ignore[attr-defined]
    return server


def serve_http(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    mcp_path: str = DEFAULT_PATH,
    transport: CapabilityMcpTransport | None = None,
    allowed_origins: tuple[str, ...] | None = None,
) -> int:
    """Run the Streamable HTTP MCP server until KeyboardInterrupt."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    server = create_http_server(
        host=host,
        port=port,
        mcp_path=mcp_path,
        transport=transport,
        allowed_origins=allowed_origins,
    )
    bound_host, bound_port = server.server_address[:2]
    _LOG.info(
        "agent-brain MCP streamable HTTP listening on http://%s:%s%s schema=%s version=%s",
        bound_host,
        bound_port,
        mcp_path,
        MCP_HTTP_SCHEMA,
        __version__,
    )
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        _LOG.info("shutdown requested")
    finally:
        server.shutdown()
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agent-brain-mcp-http",
        description=(
            "Thin Streamable HTTP MCP transport for Agent Brain cdb_context "
            "(CapabilityGateway only; no business-logic fork)."
        ),
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Bind port")
    parser.add_argument("--path", default=DEFAULT_PATH, help="MCP endpoint path")
    parser.add_argument(
        "--allow-origin",
        action="append",
        default=None,
        help="Allowed Origin header value (repeatable). Omit to allow any/non-browser.",
    )
    args = parser.parse_args(argv)
    origins = tuple(args.allow_origin) if args.allow_origin else None
    return serve_http(
        host=args.host,
        port=args.port,
        mcp_path=args.path,
        allowed_origins=origins,
    )


__all__ = [
    "DEFAULT_HOST",
    "DEFAULT_PATH",
    "DEFAULT_PORT",
    "MCP_HTTP_SCHEMA",
    "McpHttpServerState",
    "create_http_server",
    "main",
    "serve_http",
]


if __name__ == "__main__":
    raise SystemExit(main())
