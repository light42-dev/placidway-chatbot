"""Every figure in a reply must come from what the model was shown.

Prices no page lists are covered by guards/prices.py. This covers the rest: a
duration, a percentage, a count or a year that appears in no retrieved
passage and nowhere in the conversation is something the model made up.

bot/chat.py asks the model once more when it finds such a figure. Whatever
comes back is then cleaned here: the sentence stating an unsupported figure
is dropped, and if nothing is left the bot says it doesn't know.
"""
from __future__ import annotations

import re

from .. import amounts

SMALLEST_CHECKED = 10       # below this a number is usually a list marker or "one of 3 options"
NOTHING_LEFT = "I don't have that information: PlacidWay's pages don't list it."


def unsupported(text: str, shown_to_model: str) -> set[float]:
    """The numbers (10 or more) in `text` that appear nowhere in `shown_to_model`."""
    return {number for number in amounts.numbers(text) if number >= SMALLEST_CHECKED} - amounts.numbers(shown_to_model)


def drop_unsupported_figures(reply: str, shown_to_model: str) -> str:
    """Drop the sentences of `reply` that state a number found nowhere in `shown_to_model`."""
    parts = re.split(r"((?<=[.!?])\s+|\n+)", reply)         # sentences, with their separators
    kept = [part for part in parts if not unsupported(part, shown_to_model)]
    if len(kept) == len(parts):
        return reply
    return "".join(kept).strip() or NOTHING_LEFT
