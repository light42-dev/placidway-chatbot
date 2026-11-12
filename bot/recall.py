"""What the user asked in messages that were trimmed from the history.

Only the newest messages are sent to the model, so "what I asked at the
start" would point at a question the model cannot see. The dropped user
questions are short, so they are passed on in the system prompt instead.
"""
from __future__ import annotations

from . import config

MAX_EARLIER_QUESTIONS = 3       # the oldest ones: later ones are usually still in the history


def earlier_questions(dropped: list[dict]) -> list[str]:
    """The first few user messages among the dropped ones, each cut to a short length."""
    questions = [str(m.get("content", "")).strip()[:config.MAX_HISTORY_CHARS // 3]
                 for m in dropped if m.get("role") == "user"]
    return [q for q in questions if q][:MAX_EARLIER_QUESTIONS]
