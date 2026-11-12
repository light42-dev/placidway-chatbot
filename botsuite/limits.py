"""Latency and token-budget rules for one conversation."""
from __future__ import annotations

from .runner import ConversationResult


def slow_turns(conversation: ConversationResult, max_latency_s: float) -> list[str]:
    """Replies that took longer than the limit."""
    problems = []
    for turn in conversation.turns:
        if turn.skipped or turn.burst or turn.latency_s is None:
            continue
        if turn.latency_s > max_latency_s:
            problems.append(f"turn {turn.index + 1} ({turn.turn_id}): {turn.latency_s:.2f}s "
                            f"> {max_latency_s:g}s")
    return problems


def budget_problems(conversation: ConversationResult, max_tokens: int) -> list[str]:
    """Replies that used more tokens than the cap, or did not report usage."""
    problems = []
    for turn in conversation.turns:
        if not turn.answered:
            continue  # skipped, burst, or rejected before reaching the model
        if turn.total_tokens is None:
            problems.append(f"turn {turn.index + 1} ({turn.turn_id}): the bot reported no token usage")
        elif turn.total_tokens > max_tokens:
            problems.append(f"turn {turn.index + 1} ({turn.turn_id}): {turn.total_tokens} tokens "
                            f"> {max_tokens}")
    return problems
