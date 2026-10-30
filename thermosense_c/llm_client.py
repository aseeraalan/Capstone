"""HTTP call to a local Ollama server.

This file does not decide a risk category and it does not import the
RiskAssessment model. The caller passes a JSON Schema in, and passes the
raw assistant string back to assess.py for Pydantic validation.
"""

from __future__ import annotations

import http.client
import json
import time
from urllib.parse import urlparse

DEFAULT_MODEL = "llama3.2:1b"
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_TIMEOUT_S = 10.0
# A stopped local server should not use the whole generation budget.
# The full timeout still applies after a connection is accepted.
CONNECT_TIMEOUT_CAP_S = 5.0


class LlmCallError(Exception):
    """A transport or envelope failure. kind is timeout, unavailable, or invalid_response."""

    def __init__(self, kind: str, detail: str, latency_ms: int):
        super().__init__(detail)
        self.kind = kind
        self.detail = detail
        self.latency_ms = latency_ms


def chat_completion(
    *,
    url: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_s: float,
    response_schema: dict,
) -> tuple[str, int]:
    """POST one non-streaming chat request. Return the assistant text and latency."""

    body = {
        "model": model,
        "messages": messages,
        "stream": False,
        # Ollama uses this schema to constrain the reply. Pydantic checks it again later.
        "format": response_schema,
        # temperature 0 asks for the most repeatable wording. It does not make the category correct.
        "options": {"temperature": 0},
    }
    data = json.dumps(body).encode("utf-8")
    started = time.perf_counter()
    try:
        host, port, path = _split_url(url)
    except ValueError as exc:
        raise LlmCallError("unavailable", str(exc), _elapsed_ms(started)) from exc

    # Connect and read are separate on purpose.
    # If nothing accepts the connection, Ollama is not running: LLM_UNAVAILABLE.
    # If the connection opens and then the reply does not finish: TIMEOUT.
    # This Windows laptop drops packets to a closed port instead of refusing
    # them, so a missing server shows up as a connect timeout. A Raspberry Pi
    # usually reports connection refused. Both are "unavailable".
    conn = http.client.HTTPConnection(host, port, timeout=_connect_timeout(timeout_s))
    try:
        try:
            conn.connect()
        except TimeoutError as exc:
            raise LlmCallError(
                "unavailable",
                "timed out while opening a connection",
                _elapsed_ms(started),
            ) from exc
        except OSError as exc:
            raise LlmCallError("unavailable", _short(str(exc)), _elapsed_ms(started)) from exc

        if conn.sock is not None:
            conn.sock.settimeout(timeout_s)
        try:
            conn.request(
                "POST",
                path,
                body=data,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            response = conn.getresponse()
            raw = response.read(1_000_000)
            status_code = response.status
        except TimeoutError as exc:
            raise LlmCallError(
                "timeout",
                "timed out waiting for the model response",
                _elapsed_ms(started),
            ) from exc
        except (http.client.HTTPException, OSError) as exc:
            raise LlmCallError("unavailable", _short(str(exc)), _elapsed_ms(started)) from exc
    finally:
        conn.close()

    latency_ms = _elapsed_ms(started)
    if status_code >= 400:
        snippet = raw.decode("utf-8", errors="replace")
        raise LlmCallError("unavailable", _short(f"HTTP {status_code}: {snippet}"), latency_ms)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LlmCallError(
            "invalid_response",
            "Ollama did not return a JSON chat object.",
            latency_ms,
        ) from exc

    if isinstance(payload, dict) and "error" in payload and "message" not in payload:
        raise LlmCallError("unavailable", _short(str(payload.get("error"))), latency_ms)
    try:
        content = _assistant_text(payload)
    except ValueError as exc:
        # Keep the measured latency even when the chat envelope is unusable.
        raise LlmCallError("invalid_response", str(exc), latency_ms) from exc
    return content, latency_ms


def _assistant_text(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ValueError("Ollama chat object was not a JSON object.")
    message = payload.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise ValueError("Ollama chat object did not contain an assistant string.")
    return message["content"]


def _split_url(url: str) -> tuple[str, int, str]:
    parsed = urlparse(url)
    if parsed.scheme != "http" or not parsed.hostname:
        raise ValueError("Ollama URL must look like http://localhost:11434/api/chat")
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return parsed.hostname, parsed.port or 80, path


def _connect_timeout(timeout_s: float) -> float:
    return min(float(timeout_s), CONNECT_TIMEOUT_CAP_S)


def _elapsed_ms(started: float) -> int:
    return int(round((time.perf_counter() - started) * 1000))


def _short(text: str, limit: int = 300) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3] + "..."
