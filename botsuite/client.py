"""The one place that knows how to talk to the bot.

Contract (see README): the suite POSTs JSON to BOT_URL

    {"session_id": "T01-run1", "messages": [{"role": "user", "content": "..."}, ...]}

`messages` is the whole conversation so far, oldest first, ending with the
new user message. The bot answers with JSON

    {"answer": "...", "sources": ["https://..."],
     "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
     "model": "..."}

If your bot uses other field names, change `parse_reply` below; nothing else
in the suite reads the raw response.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field


@dataclass
class BotReply:
    status: int | None            # HTTP status, None if the request never completed
    answer: str = ""
    sources: list[str] = field(default_factory=list)
    total_tokens: int | None = None
    model: str | None = None
    latency_s: float = 0.0
    error: str | None = None
    retries: int = 0


def parse_reply(body: dict) -> tuple[str, list[str], int | None, str | None]:
    """Pull answer, sources, total tokens and model out of the bot's JSON."""
    answer = ""
    for key in ("answer", "reply", "response", "message", "content", "error"):
        if isinstance(body.get(key), str):
            answer = body[key]
            break

    sources: list[str] = []
    for item in body.get("sources") or body.get("citations") or []:
        if isinstance(item, str):
            sources.append(item)
        elif isinstance(item, dict) and isinstance(item.get("url"), str):
            sources.append(item["url"])

    usage = body.get("usage") or {}
    total = usage.get("total_tokens")
    if total is None:
        parts = [usage.get(a) if usage.get(a) is not None else usage.get(b)
                 for a, b in (("prompt_tokens", "input_tokens"), ("completion_tokens", "output_tokens"))]
        if all(isinstance(p, (int, float)) for p in parts):
            total = sum(parts)
    return answer, sources, int(total) if total is not None else None, body.get("model")


class BotClient:
    def __init__(self, url: str, timeout_s: float = 30.0, min_interval_s: float = 0.0,
                 retries_on_429: int = 2):
        self.url = url
        self.timeout_s = timeout_s
        self.min_interval_s = min_interval_s
        self.retries_on_429 = retries_on_429
        self._last_request_end = 0.0
        self.requests_sent = 0

    def _post_once(self, payload: dict) -> BotReply:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.url, data=data, method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "placidway-bot-tests/1.0"},
        )
        self.requests_sent += 1
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                status, raw = response.status, response.read()
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read()
        except Exception as exc:  # timeout, refused connection, DNS failure
            return BotReply(status=None, latency_s=time.perf_counter() - started,
                            error=f"{type(exc).__name__}: {exc}")
        latency = time.perf_counter() - started

        try:
            body = json.loads(raw.decode("utf-8"))
            if not isinstance(body, dict):
                raise ValueError("response is not a JSON object")
        except Exception as exc:
            error = f"HTTP {status}, body is not a JSON object ({exc})" if status == 200 else None
            return BotReply(status=status, latency_s=latency, error=error)
        answer, sources, total, model = parse_reply(body)
        return BotReply(status=status, answer=answer, sources=sources,
                        total_tokens=total, model=model, latency_s=latency)

    def send(self, messages: list[dict], session_id: str, throttle: bool = True) -> BotReply:
        """Send one turn. Waits between requests and retries a 429 after a pause."""
        payload = {"session_id": session_id, "messages": messages}
        attempt = 0
        while True:
            if throttle and self.min_interval_s:
                wait = self._last_request_end + self.min_interval_s - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
            reply = self._post_once(payload)
            self._last_request_end = time.monotonic()
            if reply.status == 429 and throttle and attempt < self.retries_on_429:
                attempt += 1
                time.sleep(max(self.min_interval_s, 1.0) * 5 * attempt)
                continue
            reply.retries = attempt
            return reply
