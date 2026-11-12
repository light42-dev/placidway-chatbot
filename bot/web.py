"""The HTTP layer: validates the request, calls bot.chat.answer, maps errors to status codes."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler

from . import config
from .chat import answer
from .llm import LLMError


def handle_chat(raw_body: bytes) -> tuple[int, dict]:
    """Return (HTTP status, JSON body) for one POST to the chat endpoint."""
    try:
        body = json.loads(raw_body.decode("utf-8"))
        messages = body["messages"]
        if not isinstance(messages, list) or not messages or messages[-1].get("role") != "user":
            return 422, {"error": "messages must be a list ending with a user message"}
    except Exception:
        return 400, {"error": "expected a JSON object with a messages list"}
    question = str(messages[-1].get("content", ""))
    if not question.strip():
        return 422, {"error": "the last message is empty"}
    if len(question) > config.MAX_INPUT_CHARS:
        return 413, {"error": f"message is longer than {config.MAX_INPUT_CHARS} characters"}
    try:
        return 200, answer(messages)
    except LLMError as exc:
        status = 429 if exc.rate_limited else 502
        return status, {"error": f"the language model is unavailable ({exc})"}
    except Exception as exc:
        return 500, {"error": f"internal error: {type(exc).__name__}"}


class ChatHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        status, body = handle_chat(self.rfile.read(length))
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *args) -> None:
        print(f"[bot] {fmt % args}", flush=True)
