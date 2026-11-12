"""Small code checks on a model reply, applied before the Source line is added.

They enforce two product rules in code rather than trusting the prompt:
- prices are given only in US dollars, as the pages list them: a sentence that
  states an amount in another currency is a conversion, so it is removed;
- a reply that says the pages lack something also points to a free quote.
"""
from __future__ import annotations

import re

_FOREIGN = (r"(?:£|€|\bGBP|\bEUR|\bMXN|\bCAD)\s?\d[\d,]*(?:\.\d+)?(?:\s?k\b)?"
            r"|\d[\d,]*(?:\.\d+)?\s?(?:k\s)?(?:£|€|GBP\b|EUR\b|MXN\b|pounds?\b|quid\b|euros?\b|pesos?\b)")
_FOREIGN_AMOUNT = re.compile(_FOREIGN, re.I)
# "(about £14,900)" or "roughly £14,900": the amount with the words around it.
_FOREIGN_ASIDE = re.compile(r"\s*\([^)]*?(?:" + _FOREIGN + r")[^)]*\)"
                            r"|,?\s*(?:or |about |approximately |approx\.? |roughly |around |~)*(?:" + _FOREIGN + r")"
                            r"(?: roughly| approximately)?", re.I)
_USD = re.compile(r"\$\s?\d|\d\s?(?:USD|US dollars)\b")
_SENTENCE = re.compile(r"(?:[^.!?\n]|\.(?=\d))+[.!?]*[ \t]*|\n+")   # "1.5" is not a sentence end
USD_ONLY = "PlacidWay's pages list prices in US dollars only."

_SAYS_UNKNOWN = re.compile(
    r"don't know|do not know|not sure|can't find|cannot find|no (information|details|mention)"
    r"|(don't|do not|doesn't|does not) (have|say|mention|state|list|include|give|provide|cover)"
    r"|(not|isn't|aren't) (listed|stated|mentioned|available|specified|provided|covered)", re.I)
_HAS_QUOTE = re.compile(r"quote|contact|consultation|reach out", re.I)
QUOTE_LINE = "You can request a free quote from PlacidWay for details."


def drop_foreign_prices(text: str) -> str:
    """Remove amounts given in a currency other than US dollars.

    In a sentence that also has a dollar price only the foreign amount goes;
    any other sentence with a foreign amount is removed whole.
    """
    if not _FOREIGN_AMOUNT.search(text):
        return text
    kept = []
    for sentence in _SENTENCE.findall(text):
        if _FOREIGN_AMOUNT.search(sentence):
            if not _USD.search(sentence):
                continue
            sentence = _FOREIGN_ASIDE.sub("", sentence)
        kept.append(sentence)
    return ("".join(kept).strip() + " " + USD_ONLY).strip()


def add_quote_pointer(text: str) -> str:
    """Make sure a reply that admits missing information suggests a free quote."""
    plain = text.replace("’", "'")
    if _SAYS_UNKNOWN.search(plain) and not _HAS_QUOTE.search(plain):
        return text.rstrip() + " " + QUOTE_LINE
    return text


def tidy_reply(text: str) -> str:
    return add_quote_pointer(drop_foreign_prices(text))
