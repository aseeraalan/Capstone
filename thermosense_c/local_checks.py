"""Local stand-ins for Ollama unavailable, timeout, and a bad model reply.

These checks exist so the failure path can be shown on a laptop without
installing a model and without contacting a cloud API. They are not sensor tests.
"""

from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from thermosense_c.assess import interpret
from thermosense_c.llm_client import DEFAULT_MODEL
from thermosense_c.samples import normal_features
from thermosense_c.schemas import InterfaceReport


def check_unavailable() -> InterfaceReport:
    """Point at a closed local port, which stands in for Ollama not running."""

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return interpret(
        normal_features(),
        mode="ollama",
        timeout_s=0.4,
        ollama_url=f"http://127.0.0.1:{port}/api/chat",
    )


def check_timeout(timeout_s: float = 0.4) -> InterfaceReport:
    """Accept a connection and never send an HTTP reply."""

    ready = threading.Event()
    release = threading.Event()
    state: dict[str, int] = {}

    def _listen() -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", 0))
            sock.listen(1)
            sock.settimeout(2)
            state["port"] = sock.getsockname()[1]
            ready.set()
            try:
                conn, _ = sock.accept()
            except socket.timeout:
                return
            try:
                release.wait(timeout=5)
            finally:
                conn.close()
        finally:
            sock.close()

    thread = threading.Thread(target=_listen, daemon=True)
    thread.start()
    if not ready.wait(timeout=2):
        raise RuntimeError("timeout stand-in did not start")
    try:
        return interpret(
            normal_features(),
            mode="ollama",
            timeout_s=timeout_s,
            ollama_url=f"http://127.0.0.1:{state['port']}/api/chat",
        )
    finally:
        release.set()
        thread.join(timeout=2)


def check_malformed_response() -> InterfaceReport:
    """Return a category name that is not normal, elevated, or high-risk."""

    content = json.dumps(
        {
            "risk_category": "critical",
            "reason": "This label is not one of the three allowed categories.",
            "recommendation": "Do not treat this text as a classification.",
        }
    )
    return interpret_with_fake_ollama(content)


def run_failure_checks() -> list[InterfaceReport]:
    return [check_unavailable(), check_timeout(), check_malformed_response()]


def interpret_with_fake_ollama(
    assistant_content: str,
    features: dict | None = None,
    model: str = DEFAULT_MODEL,
    capture: dict | None = None,
) -> InterfaceReport:
    """One chat request against an in-process fake of the Ollama HTTP envelope."""

    http_body = json.dumps(
        {"message": {"role": "assistant", "content": assistant_content}}
    ).encode("utf-8")
    return _interpret_against_http_body(http_body, features=features, model=model, capture=capture)


def _interpret_against_http_body(
    http_body: bytes,
    *,
    features: dict | None,
    model: str,
    capture: dict | None,
) -> InterfaceReport:
    server = _ReadyServer(("127.0.0.1", 0), _Handler)
    server.http_body = http_body
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    if not server.ready.wait(timeout=2):
        server.server_close()
        raise RuntimeError("fake Ollama server did not start")
    port = server.server_address[1]
    try:
        report = interpret(
            normal_features() if features is None else features,
            mode="ollama",
            model=model,
            timeout_s=2,
            ollama_url=f"http://127.0.0.1:{port}/api/chat",
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    if capture is not None:
        capture["body"] = json.loads(server.captured.decode("utf-8"))
    return report


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        self.server.captured = self.rfile.read(length)  # type: ignore[attr-defined]
        body = self.server.http_body  # type: ignore[attr-defined]
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class _ReadyServer(HTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], handler: type[BaseHTTPRequestHandler]):
        super().__init__(server_address, handler)
        self.ready = threading.Event()
        self.captured = b""
        self.http_body = b""

    def serve_forever(self, poll_interval: float = 0.05):  # type: ignore[override]
        self.ready.set()
        return super().serve_forever(poll_interval=poll_interval)
