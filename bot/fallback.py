"""Make sure an "I don't know" reply points the user to a free quote.

The rules say every unanswered question should end with that suggestion. The
model usually adds it, but not always (for example when it only says the
pages don't mention something), so the code adds it when it is missing.
"""
from __future__ import annotations

import re

# The reply says the pages do not have the answer.
SAYS_UNKNOWN = re.compile(
    r"\b(don'?t|do not|doesn'?t|does not) (know|list|mention|say|state|include|cover|describe|give|provide)"
    r"|\b(not|isn'?t|aren'?t) (listed|stated|mentioned|described|covered|included|specified)"
    r"|\bno (information|details|mention)\b",
    re.I,
)
# The reply already points to a quote or to a person.
HAS_POINTER = re.compile(r"quote|contact|reach out|consultation", re.I)

QUOTE_LINE = "You can request a free quote from PlacidWay to ask about this."
SOURCE_SPLIT = "\n\nSource:"


def add_quote_pointer(text: str) -> str:
    """Append the free-quote suggestion to an "I don't know" reply that lacks one."""
    body, sep, source = text.partition(SOURCE_SPLIT)
    normalized = body.replace("’", "'")
    if not SAYS_UNKNOWN.search(normalized) or HAS_POINTER.search(body):
        return text
    return body.rstrip() + " " + QUOTE_LINE + sep + source
