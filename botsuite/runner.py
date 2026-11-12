"""Play a persona's whole conversation against the bot and grade every reply."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

from .checks import evaluate, loose_numbers
from .client import BotClient
from .scenarios import Persona, Turn


@dataclass
class TurnResult:
    persona_id: str
    run: int
    turn_id: str
    index: int
    tags: list[str]
    user: str
    status: int | None = None
    reply: str = ""
    sources: list[str] = field(default_factory=list)
    latency_s: float | None = None
    total_tokens: int | None = None
    model: str | None = None
    error: str | None = None
    retries: int = 0
    checks: list[dict] = field(default_factory=list)
    skipped: str | None = None
    burst: dict | None = None

    @property
    def failures(self) -> list[dict]:
        return [c for c in self.checks if not c["passed"]]

    @property
    def passed(self) -> bool:
        return not self.failures

    @property
    def answered(self) -> bool:
        """True for an ordinary turn the bot answered with HTTP 200."""
        return self.skipped is None and self.burst is None and self.status == 200


@dataclass
class ConversationResult:
    persona_id: str
    run: int
    turns: list[TurnResult]

    def to_dict(self) -> dict:
        return asdict(self)


def _shorten(text: str, limit: int = 400) -> str:
    return text if len(text) <= limit else f"{text[:200]} … [{len(text)} characters] … {text[-100:]}"


class Runner:
    def __init__(self, client: BotClient, run_abuse: bool = False,
                 canary: str | None = None, cooldown_scale: float = 1.0):
        self.client = client
        self.run_abuse = run_abuse
        self.canary = canary
        self.cooldown_scale = cooldown_scale

    def run_conversation(self, persona: Persona, run: int) -> ConversationResult:
        """Send the persona's turns in order, carrying the full history."""
        session_id = f"{persona.id}-run{run}"
        history: list[dict] = []
        user_numbers: set[int] = set()
        results: list[TurnResult] = []

        for index, turn in enumerate(persona.turns):
            result = TurnResult(persona.id, run, turn.id, index, turn.tags, _shorten(turn.user))
            results.append(result)

            if turn.abuse and not self.run_abuse:
                result.skipped = "abuse turn, run with --run-abuse"
                continue
            if turn.burst:
                self._burst(turn, session_id, result)
            else:
                self._ordinary(turn, session_id, history, user_numbers, result)
            if turn.cooldown_s:
                time.sleep(turn.cooldown_s * self.cooldown_scale)
        return ConversationResult(persona.id, run, results)

    def _ordinary(self, turn: Turn, session_id: str, history: list[dict],
                  user_numbers: set[int], result: TurnResult) -> None:
        user_numbers |= loose_numbers(turn.user)
        messages = history + [{"role": "user", "content": turn.user}]
        reply = self.client.send(messages, session_id)

        result.status, result.reply, result.sources = reply.status, reply.answer, reply.sources
        result.latency_s, result.total_tokens = reply.latency_s, reply.total_tokens
        result.model, result.error, result.retries = reply.model, reply.error, reply.retries
        result.checks = [c.to_dict() for c in evaluate(
            turn.expect, status=reply.status, reply=reply.answer, sources=reply.sources,
            user_numbers=user_numbers, allow_status=turn.allow_status,
            error=reply.error, canary=self.canary)]

        # A real chat window keeps the exchange only if the bot answered.
        if reply.status == 200:
            history.append({"role": "user", "content": turn.user})
            history.append({"role": "assistant", "content": reply.answer})

    def _burst(self, turn: Turn, session_id: str, result: TurnResult) -> None:
        """Fire the same message many times with no pause, outside the chat history."""
        messages = [{"role": "user", "content": turn.user}]
        statuses = [self.client.send(messages, f"{session_id}-burst", throttle=False).status
                    for _ in range(turn.burst)]
        answered = sum(1 for s in statuses if s == 200)
        throttled = sum(1 for s in statuses if s in (429, 503))
        broken = [s for s in statuses if s is None or (s >= 500 and s != 503)]
        result.burst = {"sent": turn.burst, "answered": answered, "throttled": throttled,
                        "broken": len(broken)}
        result.checks = [{
            "name": "survives_burst", "passed": not broken,
            "detail": "" if not broken else f"{len(broken)} of {turn.burst} requests crashed or timed out",
        }]
