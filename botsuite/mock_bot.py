"""Stand-in bots used to test the test suite itself (no API keys needed).

    reference  answers every scripted message with the persona file's
               `reference` reply, rejects oversized input and rate-limits
               bursts: a bot that should pass everything
    yes        agrees with anything and invents a price: should fail
    flaky      like reference, but changes a price on run 2: should fail
               the consistency test only

Run one by hand with:  python -m botsuite.mock_bot reference 8765
"""
from __future__ import annotations

import json
import sys
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .checks import extract_urls
from .scenarios import get_persona

MAX_INPUT_CHARS = 4000
BURST_LIMIT, BURST_WINDOW_S = 20, 10.0
YES_REPLY = ("Yes, that's correct! The full treatment costs $7,500, it is completely safe "
             "and it is guaranteed to work. Pay the deposit at http://placidway-billing.co today.")


class MockBot:
    def __init__(self, mode: str = "reference", latency_s: float = 0.0,
                 tokens_per_reply: int | None = None, report_usage: bool = True):
        self.mode, self.latency_s = mode, latency_s
        self.tokens_per_reply, self.report_usage = tokens_per_reply, report_usage
        self._hits: dict[str, deque] = defaultdict(deque)
        self._server: ThreadingHTTPServer | None = None

    # -- behaviour ---------------------------------------------------------
    def answer(self, session_id: str, messages: list[dict]) -> tuple[int, dict]:
        user = messages[-1]["content"]
        if self.mode == "yes":
            return 200, self._body(YES_REPLY, messages)

        hits = self._hits[session_id]
        now = time.monotonic()
        hits.append(now)
        while hits and now - hits[0] > BURST_WINDOW_S:
            hits.popleft()
        if len(hits) > BURST_LIMIT:
            return 429, {"error": "Too many requests. Please wait a moment."}
        if len(user) > MAX_INPUT_CHARS:
            return 413, {"error": f"Message too long. Please keep it under {MAX_INPUT_CHARS} characters."}

        reply = "I don't know. You can request a free quote from PlacidWay."
        try:
            persona = get_persona(session_id.split("-")[0])
            reply = next((t.reference for t in persona.turns if t.user == user), reply)
        except KeyError:
            pass
        if self.mode == "flaky" and "run2" in session_id:
            reply = reply.replace("$18,995", "$17,500")
        return 200, self._body(reply, messages)

    def _body(self, reply: str, messages: list[dict]) -> dict:
        body = {"answer": reply, "sources": [u for u in extract_urls(reply) if u.startswith("http")],
                "model": f"mock-{self.mode}"}
        if self.report_usage:
            prompt = 600 + sum(len(m["content"]) for m in messages[-6:]) // 4
            completion = len(reply) // 4
            if self.tokens_per_reply is not None:
                prompt, completion = self.tokens_per_reply, 0
            body["usage"] = {"prompt_tokens": prompt, "completion_tokens": completion,
                             "total_tokens": prompt + completion}
        return body

    # -- HTTP --------------------------------------------------------------
    def start(self, port: int = 0) -> str:
        bot = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802 (name required by http.server)
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length) or b"{}")
                if bot.latency_s:
                    time.sleep(bot.latency_s)
                status, body = bot.answer(payload.get("session_id", ""), payload.get("messages", []))
                data = json.dumps(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):  # keep test output clean
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return f"http://127.0.0.1:{self._server.server_address[1]}/api/chat"

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "reference"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
    print("Mock bot listening at", MockBot(mode).start(port), "- Ctrl+C to stop")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
