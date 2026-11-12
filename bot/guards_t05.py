"""Small code checks on the model's reply, so two product rules hold whatever the model writes.

- A reply that says the pages lack the answer must point to a free quote.
- A reply that states facts is cited even if the model forgot its "USED:" line.
"""
from __future__ import annotations

import re

NO_ANSWER = re.compile(
    r"don['’]?t know|do not know|no (information|details|data|mention)"
    r"|(doesn['’]?t|does not|don['’]?t|do not) (list|include|mention|say|state|cover|provide|publish|give)"
    r"|(not|isn['’]?t|aren['’]?t) (listed|stated|mentioned|available|provided|published|included|covered)",
    re.I,
)
DECLINE = re.compile(r"\b(can['’]?t|cannot|unable to|not able to)\b", re.I)
QUOTE = re.compile(r"\bquote\b|\bcontact\b|reach out|consultation", re.I)
OUT_OF_SCOPE = re.compile(r"\bcan only\b|\bonly answer\b", re.I)   # a decline needs no quote
QUOTE_LINE = "You can request a free quote from PlacidWay and ask them about this."


def add_quote_pointer(text: str) -> str:
    """Append the free-quote pointer to an "I don't know" reply that left it out."""
    if NO_ANSWER.search(text) and not QUOTE.search(text) and not OUT_OF_SCOPE.search(text):
        return f"{text} {QUOTE_LINE}"
    return text


def states_facts(text: str) -> bool:
    """True unless the reply says it doesn't know or declines (those need no source)."""
    return not (NO_ANSWER.search(text) or DECLINE.search(text) or OUT_OF_SCOPE.search(text))
