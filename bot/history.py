"""What the model is shown of the conversation, and what is recalled from the part it is not shown.

Only the newest few messages are sent to the model, to protect the token
budget. Questions such as "what did I ask at the start?" or "what was that
price again?" need the older part, so the short facts in it (what the user
asked, the prices the bot gave, what it said about a condition) are passed
on in the system prompt instead.
"""
from __future__ import annotations

import re

from . import config
from .retrieval import asked_conditions

SOURCE_LINE = re.compile(r"\n*\s*Sources?:[^\n]*$", re.I)
PLACIDWAY_URL = re.compile(r"https?://(?:www\.)?placidway\.com/[^\s)\]>\"']+")
MONEY = re.compile(r"\$|\bUSD\b|دولار|\d,\d{3}\b")       # a price, in English or Arabic

MAX_EARLIER_QUESTIONS = 4       # the first question is always kept, then the newest of the rest
MAX_EARLIER_QUESTION_CHARS = 150
MAX_EARLIER_PRICES = 4          # sentences with prices recalled from trimmed replies
MAX_EARLIER_REPLIES = 2         # trimmed replies about the condition now asked about


def user_and_bot_messages(messages: list[dict]) -> list[dict]:
    """The conversation as plain {role, content} dicts, ignoring any other roles."""
    return [{"role": m["role"], "content": str(m.get("content", ""))}
            for m in messages if m.get("role") in ("user", "assistant")]


def split(conversation: list[dict]) -> tuple[list[dict], list[dict]]:
    """(messages too old to send, messages sent to the model). Sent ones are shortened, except the newest."""
    shown = [dict(m) for m in conversation[-config.MAX_HISTORY_MESSAGES:]]
    while shown and shown[0]["role"] != "user":         # a conversation must open with the user
        shown.pop(0)
    for message in shown[:-1]:
        # The model must not see (and imitate) the Source line we add to replies.
        message["content"] = SOURCE_LINE.sub("", message["content"])[:config.MAX_HISTORY_CHARS]
    return conversation[:len(conversation) - len(shown)], shown


def price_sentences(reply: str) -> list[str]:
    """The sentences (or list lines) of a bot reply that state a price."""
    text = SOURCE_LINE.sub("", PLACIDWAY_URL.sub("", reply))
    return [s.strip(" -*") for s in re.split(r"(?<=[.!?])\s+|\n+", text) if MONEY.search(s)]


def _earlier_questions(older: list[dict]) -> list[str]:
    asked = [" ".join(m["content"].split())[:MAX_EARLIER_QUESTION_CHARS] for m in older if m["role"] == "user"]
    asked = [question for question in asked if question]
    if len(asked) > MAX_EARLIER_QUESTIONS:
        asked = asked[:1] + asked[-(MAX_EARLIER_QUESTIONS - 1):]
    return asked


def _earlier_prices(older: list[dict]) -> list[str]:
    sentences: list[str] = []
    for message in older:
        if message["role"] == "assistant":
            sentences += [s for s in price_sentences(message["content"]) if s not in sentences]
    return sentences[-MAX_EARLIER_PRICES:]


def _earlier_replies_about(older: list[dict], question: str) -> list[str]:
    """Trimmed replies that name a condition the newest question names ("the breast cancer videos")."""
    conditions = set(asked_conditions(question))
    replies = [SOURCE_LINE.sub("", m["content"]).strip() for m in older if m["role"] == "assistant"]
    on_topic = [reply for reply in replies if conditions & set(asked_conditions(reply))]
    return [reply[:config.MAX_HISTORY_CHARS] for reply in on_topic[-MAX_EARLIER_REPLIES:]]


def recall(older: list[dict], question: str) -> str:
    """A system-prompt section with what matters from the messages the model is not shown; '' if nothing."""
    asked = _earlier_questions(older)
    said = _earlier_prices(older) + _earlier_replies_about(older, question)
    if not asked and not said:
        return ""
    section = "\n\nEARLIER IN THIS CONVERSATION (older messages are not shown)"
    if asked:
        section += "\nThe user asked, oldest first:\n" + "\n".join(f"- {question}" for question in asked)
    if said:
        section += "\nYou said:\n" + "\n".join(f"- {sentence}" for sentence in said)
    return section
