"""Checks on the model's reply that plain code does more reliably than the prompt.

1. A sentence stating a dollar amount that appears on none of the 7 pages
   (and that the user did not bring up) is removed. This catches made-up
   totals such as "$30,000 plus extras is about $31,400".
2. A reply that says the pages don't have the answer always ends by pointing
   to a free quote from PlacidWay.

The model's final "USED: ..." line is kept last, so bot/chat.py can still
turn it into a Source line.
"""
from __future__ import annotations

import re
from functools import lru_cache

from .config import ROOT

# "$18,995", "$ 30k", "18,995 USD", "2600 dollars"
_MONEY = re.compile(
    r"(?:US)?\$\s?(\d[\d,]*(?:\.\d+)?)(\s?k\b)?"
    r"|(\d[\d,]*(?:\.\d+)?)(\s?k\b)?\s?(?:USD|US dollars?|dollars?)\b",
    re.I,
)
# Any number, for the pages and the user's own messages ("like 31k").
_NUMBER = re.compile(r"(\d[\d,]*(?:\.\d+)?)(\s?k\b)?", re.I)
_USED_LINE = re.compile(r"\n?\s*USED:[^\n]*\s*$", re.I)

# The reply says the pages lack the answer ...
_NOT_LISTED = re.compile(
    r"\b(don['’]?t|do not|doesn['’]?t|does not) (know|list|say|mention|state)\b"
    r"|\bnot (listed|stated|mentioned|specified)\b|\bno information\b", re.I)
# ... and already points somewhere useful.
_HAS_POINTER = re.compile(r"quote|contact|reach out|consultation", re.I)
QUOTE_LINE = "You can request a free quote from PlacidWay to ask about this."
# Used only if every sentence of the reply stated an unlisted amount.
NO_FIGURE = "I can't confirm that figure: PlacidWay's pages don't list it."


def _to_int(number: str, k: str | None) -> int | None:
    try:
        value = float(number.replace(",", ""))
    except ValueError:
        return None
    return int(value * 1000) if k else int(value)


def _numbers(text: str) -> set[int]:
    found = {_to_int(m.group(1), m.group(2)) for m in _NUMBER.finditer(text)}
    return found - {None}


def _amounts(text: str) -> set[int]:
    found = set()
    for m in _MONEY.finditer(text):
        number, k = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        found.add(_to_int(number, k))
    return found - {None}


@lru_cache(maxsize=1)
def page_numbers() -> frozenset[int]:
    """Every number written anywhere on the crawled pages."""
    numbers: set[int] = set()
    for path in (ROOT / "data" / "pages").glob("*.txt"):
        numbers |= _numbers(path.read_text(encoding="utf-8"))
    return frozenset(numbers)


def drop_unlisted_prices(text: str, user_messages: list[str]) -> str:
    """Remove each sentence that states a dollar amount found neither on the pages nor in the user's words."""
    allowed = set(page_numbers())
    for message in user_messages:
        allowed |= _numbers(message)
    lines = []
    for line in text.split("\n"):
        sentences = re.split(r"(?<=[.!?])\s+", line)
        kept = [s for s in sentences if _amounts(s) <= allowed]
        if kept or not line.strip():
            lines.append(" ".join(kept))
    return "\n".join(lines).strip() or NO_FIGURE


def ensure_quote_pointer(text: str) -> str:
    """A "the pages don't say" reply must suggest a free quote."""
    if _NOT_LISTED.search(text) and not _HAS_POINTER.search(text):
        text = text.rstrip() + " " + QUOTE_LINE
    return text


def check_reply(text: str, user_messages: list[str]) -> str:
    """Apply both guards to the model's reply, keeping its final USED line last."""
    used = _USED_LINE.search(text)
    tail = used.group(0) if used else ""
    body = text[:used.start()] if used else text
    body = ensure_quote_pointer(drop_unlisted_prices(body, user_messages))
    return body + ("\n" + tail.strip() if tail else "")
