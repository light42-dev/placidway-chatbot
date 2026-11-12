"""Remembering what the user asked before the history was trimmed.

Only the newest messages are sent to the model (config.MAX_HISTORY_MESSAGES).
A question such as "how long was that program I asked about first" needs the
opening question, which by then has been cut. The user's earlier questions
are short, so they are added to the system prompt as a list.
"""
from __future__ import annotations

MAX_QUESTIONS = 4          # the first question is always kept, then the newest of the rest
MAX_QUESTION_CHARS = 150


def earlier_questions(dropped: list[dict]) -> str:
    """A prompt section listing the user messages that were trimmed from the history."""
    questions = [" ".join(str(m.get("content", "")).split())[:MAX_QUESTION_CHARS]
                 for m in dropped if m.get("role") == "user"]
    questions = [q for q in questions if q]
    if len(questions) > MAX_QUESTIONS:
        questions = questions[:1] + questions[-(MAX_QUESTIONS - 1):]
    if not questions:
        return ""
    return ("\n\nTHE USER'S EARLIER MESSAGES, OLDEST FIRST (cut from the message history):\n"
            + "\n".join(f"- {q}" for q in questions))
