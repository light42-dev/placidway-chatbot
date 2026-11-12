"""Every figure in a reply must come from what the model was shown.

Prices are covered by guards/prices.py. This covers the rest: a duration, a
percentage, a count or a year that appears in no retrieved passage and
nowhere in the conversation is something the model made up. The sentence
stating it is dropped; if nothing is left, the bot says it doesn't know.

No second model call is made to repair the reply: it would double the
tokens the reply costs.
"""
from __future__ import annotations

import re

from .. import amounts

SMALLEST_CHECKED = 10       # below this a number is usually a list marker or "one of 3 options"
NOTHING_LEFT = "I don't have that information: PlacidWay's pages don't list it."


def drop_unsupported_figures(reply: str, shown_to_model: str) -> str:
    """Drop the sentences of `reply` that state a number found nowhere in `shown_to_model`."""
    supported = amounts.numbers(shown_to_model)

    def invented(sentence: str) -> bool:
        return any(number >= SMALLEST_CHECKED and number not in supported for number in amounts.numbers(sentence))

    parts = re.split(r"((?<=[.!?])\s+|\n+)", reply)         # sentences, with their separators
    kept = [part for part in parts if not invented(part)]
    if len(kept) == len(parts):
        return reply
    return "".join(kept).strip() or NOTHING_LEFT
