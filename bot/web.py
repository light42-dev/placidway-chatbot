"""The HTTP layer: validates the request, calls bot.chat.answer, maps errors to status codes.

The rate limit and the reply cache live in memory, so on a serverless host
they only cover requests that reach the same warm instance.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler

from . import config
from .chat import answer
from .guards.abuse import RateLimiter, ReplyCache
from .llm import LLMError

_limiter = RateLimiter(config.RATE_LIMIT_REQUESTS, config.RATE_LIMIT_WINDOW_S)
_cache = ReplyCache(config.REPLY_CACHE_TTL_S)


def handle_chat(raw_body: bytes, client_ip: str = "") -> tuple[int, dict]:
    """Return (HTTP status, JSON body) for one POST to the chat endpoint."""
    try:
        body = json.loads(raw_body.decode("utf-8"))
        messages = body["messages"]
        if not isinstance(messages, list) or not messages or messages[-1].get("role") != "user":
            return 422, {"error": "messages must be a list ending with a user message"}
    except Exception:
        return 400, {"error": "expected a JSON object with a messages list"}
    session = body.get("session_id") if isinstance(body.get("session_id"), str) else ""
    if not _limiter.allow(session or client_ip):
        return 429, {"error": "too many requests; please wait a few seconds and try again"}
    question = str(messages[-1].get("content", ""))
    if not question.strip():
        return 422, {"error": "the last message is empty"}
    if len(question) > config.MAX_INPUT_CHARS:
        return 413, {"error": f"message is longer than {config.MAX_INPUT_CHARS} characters"}
    cached = _cache.get(messages)
    if cached:
        return 200, cached
    try:
        reply = answer(messages)
        _cache.put(messages, reply)
        return 200, reply
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
        status, body = handle_chat(self.rfile.read(length), self.client_address[0])
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *args) -> None:
        print(f"[bot] {fmt % args}", flush=True)
