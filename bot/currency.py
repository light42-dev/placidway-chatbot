"""Remove amounts the model converted into another currency.

The pages list prices in US dollars only, so a figure such as "about 25,900 CAD"
or "C$26,000" can only be the model's own conversion: an invented price. The
prompt forbids conversions; this is the code-side guarantee.
"""
from __future__ import annotations

import re

_CODES = r"CAD|CDN|AUD|NZD|EUR|GBP|MXN|INR|JPY|CHF|pesos?|euros?|Canadian dollars?"
_SYMBOLS = r"C\$|CA\$|CDN\$|A\$|AU\$|NZ\$|MX\$|€|£|¥|₹"
_NUMBER = r"\d[\d,.]*\d|\d"

FOREIGN_AMOUNT = re.compile(
    rf"(?:\b(?:{_CODES})\s?\$?\s?(?:{_NUMBER})|(?<![A-Za-z])(?:{_SYMBOLS})\s?(?:{_NUMBER})|(?:{_NUMBER})\s?(?:{_CODES})\b)",
    re.IGNORECASE,
)
_PARENTHESES = re.compile(r"\s*\([^()]*\)")


def drop_converted_amounts(text: str) -> str:
    """Delete brackets, then whole sentences, that state a non-US-dollar amount."""
    if not FOREIGN_AMOUNT.search(text):
        return text
    text = _PARENTHESES.sub(lambda m: "" if FOREIGN_AMOUNT.search(m.group(0)) else m.group(0), text)
    lines = []
    for line in text.split("\n"):
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", line) if not FOREIGN_AMOUNT.search(s)]
        lines.append(" ".join(sentences))
    return "\n".join(lines).strip()
