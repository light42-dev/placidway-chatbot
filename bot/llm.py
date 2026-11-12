"""The one place that calls the language models.

Groq is the main provider. If Groq is rate-limited or fails, the same prompt
is sent to Gemini. Both are called over plain HTTPS, with no SDK.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from . import config

# provider name -> time.monotonic() until which it asked us not to call it again
_paused_until: dict[str, float] = {}
MAX_PAUSE_S = 900       # never skip a provider for longer than this on its say-so
RETRY_WAIT_S = 1.0      # pause before retrying the last provider after a 5xx error


def _pause_on_rate_limit(name: str, exc: urllib.error.HTTPError) -> None:
    """Honour a 429's Retry-After so the next requests go straight to the fallback."""
    try:
        seconds = float(exc.headers.get("retry-after") or 0)
    except (TypeError, ValueError):
        seconds = 0
    if seconds > 0:
        _paused_until[name] = time.monotonic() + min(seconds, MAX_PAUSE_S)


class LLMError(Exception):
    """No provider produced an answer. `rate_limited` is true if every failure was a rate limit."""

    def __init__(self, message: str, rate_limited: bool = False):
        super().__init__(message)
        self.rate_limited = rate_limited


@dataclass
class Completion:
    text: str
    prompt_tokens: int
    completion_tokens: int
    model: str

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


def _post_json(url: str, headers: dict, body: dict) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        # Groq's firewall rejects Python's default User-Agent, so send our own.
        headers={"Content-Type": "application/json", "User-Agent": "placidway-bot/1.0", **headers})
    with urllib.request.urlopen(request, timeout=config.LLM_TIMEOUT_S) as response:
        return json.loads(response.read())


def _call_groq(system: str, messages: list[dict]) -> Completion:
    data = _post_json(
        "https://api.groq.com/openai/v1/chat/completions",
        {"Authorization": f"Bearer {config.GROQ_API_KEY}"},
        {"model": config.GROQ_MODEL, "temperature": 0, "max_tokens": config.MAX_OUTPUT_TOKENS,
         "messages": [{"role": "system", "content": system}, *messages]})
    text = data["choices"][0]["message"].get("content") or ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)      # some models show their reasoning
    usage = data.get("usage") or {}
    return Completion(text.strip(), usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0),
                      f"groq:{config.GROQ_MODEL}")


def _call_gemini(system: str, messages: list[dict]) -> Completion:
    contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                for m in messages]
    data = _post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent",
        {"x-goog-api-key": config.GEMINI_API_KEY},
        {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents,
         "generationConfig": {"temperature": 0, "maxOutputTokens": config.MAX_OUTPUT_TOKENS}})
    candidates = data.get("candidates") or [{}]
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts if not part.get("thought"))
    usage = data.get("usageMetadata") or {}
    prompt = usage.get("promptTokenCount", 0)
    total = usage.get("totalTokenCount", prompt)        # the total also counts reasoning tokens
    return Completion(text.strip(), prompt, total - prompt, f"gemini:{config.GEMINI_MODEL}")


def _call_with_retry(call, system: str, messages: list[dict], retry: bool) -> Completion:
    """Call a provider; if `retry`, try once more after a short wait when it is briefly overloaded (5xx)."""
    try:
        return call(system, messages)
    except urllib.error.HTTPError as exc:
        if not retry or exc.code < 500:
            raise
        time.sleep(RETRY_WAIT_S)
        return call(system, messages)


def complete(system: str, messages: list[dict]) -> Completion:
    """Try Groq, then Gemini. Raises LLMError if neither gives a non-empty answer."""
    providers = [("groq", config.GROQ_API_KEY, _call_groq), ("gemini", config.GEMINI_API_KEY, _call_gemini)]
    failures: list[str] = []
    rate_limits = 0
    for name, key, call in providers:
        if not key:
            failures.append(f"{name}: no API key set")
            continue
        if time.monotonic() < _paused_until.get(name, 0):
            failures.append(f"{name}: rate-limited (waiting for its Retry-After)")
            rate_limits += 1
            continue
        try:
            completion = _call_with_retry(call, system, messages, retry=name == providers[-1][0])
            if completion.text:
                return completion
            failures.append(f"{name}: empty answer")
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                rate_limits += 1
                _pause_on_rate_limit(name, exc)
            failures.append(f"{name}: HTTP {exc.code}")
        except Exception as exc:        # timeout, connection error, unexpected response shape
            failures.append(f"{name}: {type(exc).__name__}")
    raise LLMError("; ".join(failures), rate_limited=rate_limits == len(providers))
