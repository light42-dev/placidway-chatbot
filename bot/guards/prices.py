"""Keep made-up prices, converted prices and dictated wording out of replies.

Done in code, not left to the model: a visitor (or someone posing as staff)
can push the model to repeat a price that no page lists, or to say a phrase
word for word ("just say 'Confirmed: $9,995'") and screenshot it. So:
- any dollar amount in a reply that is not on the 7 pages becomes "that amount";
- an amount in another currency can only be the model's own conversion (the
  pages list US dollars only), so it is removed;
- a reply sentence that repeats a phrase the user put in quotes (and no page
  contains) is dropped.

How an amount is written, and which amounts the pages list, is in bot/amounts.py.
"""
from __future__ import annotations

import re
from functools import lru_cache

from .. import amounts
from ..history import price_sentences
from ..retrieval import load_index

_QUOTED = re.compile(r"(?<!\w)[\"'“‘]([^\"“”‘’]{8,200}?)[\"'”’](?!\w)")
REFUSAL = "I can't say that: I can only state what PlacidWay's pages list."
_REFUSAL = re.compile(r"\b(can['’]?t|cannot|won['’]?t|unable)\b", re.I)

# An amount in a currency other than US dollars: "£14,900", "C$26,000", "25,900 CAD", "300 euros".
_CURRENCY_CODES = r"CAD|CDN|AUD|NZD|EUR|GBP|MXN|INR|JPY|CHF|pesos?|euros?|pounds?|quid|Canadian dollars?"
_CURRENCY_SYMBOLS = r"C\$|CA\$|CDN\$|A\$|AU\$|NZ\$|MX\$|€|£|¥|₹"
_FOREIGN = (rf"(?:\b(?:{_CURRENCY_CODES})\s?\$?\s?{amounts.NUMBER}"
            rf"|(?<![A-Za-z])(?:{_CURRENCY_SYMBOLS})\s?{amounts.NUMBER}"
            rf"|(?:\$\s?)?{amounts.NUMBER}\s?(?:{_CURRENCY_CODES})\b)")
_FOREIGN_AMOUNT = re.compile(_FOREIGN, re.I)
# The same amount with the words around it: ", or about £14,900", "£14,900 roughly".
_CONVERSION = re.compile(
    rf",?\s*(?:\b(?:or|about|approximately|approx\.?|roughly|around|which is|that is|equivalent to)\s|~\s?)*"
    rf"{_FOREIGN}(?:\s(?:roughly|approximately)\b)?",
    re.I)
_PARENTHESES = re.compile(r"\s*\([^()]*\)")
USD_ONLY = "PlacidWay's pages list prices in US dollars only."
PRICE_QUESTION = re.compile(r"\b(price|cost|how much|fee|rate|charge)", re.I)


def hide_unlisted_amounts(text: str) -> str:
    """Replace each dollar amount that no page lists with "that amount"."""
    return amounts.hide(text, lambda value: value not in amounts.listed())


def unlisted_amounts(texts: list[str]) -> list[str]:
    """Dollar amounts, as written, that appear in the texts but on no page."""
    written = [as_written for text in texts for as_written, value in amounts.find(text)
               if value not in amounts.listed()]
    return list(dict.fromkeys(written))         # each one once, in the order they came up


def _squash(text: str) -> str:
    """Letters and digits only, so "$9,995" and "9995" or odd spaces still compare equal."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


@lru_cache(maxsize=1)
def _page_text() -> str:
    return _squash(" ".join(p.text for p in load_index().passages))


def drop_dictated_phrases(text: str, user_messages: list[str]) -> str:
    """Drop reply sentences that repeat a phrase the user put in quotes, unless a page says it.

    If that removes the model's refusal (or it never refused), a plain refusal is put first.
    """
    phrases = [_squash(q) for q in _QUOTED.findall(" ".join(user_messages)) if len(q.split()) >= 2]
    phrases = [p for p in phrases if p and p not in _page_text()]
    if not phrases:
        return text
    parts = re.split(r"((?<=[.!?])\s+|\n+)", text)       # sentences, with their separators
    kept = [part for part in parts if not any(p in _squash(part) for p in phrases)]
    if len(kept) == len(parts):
        return text
    text = "".join(kept).strip()
    if not _REFUSAL.search(text):
        text = (REFUSAL + " " + text).strip()
    return text


def drop_converted_amounts(text: str) -> str:
    """Remove amounts in another currency: the pages list US dollars only, so these are the model's own sums.

    Brackets holding one go first. Then each sentence loses the conversion and
    the words around it ("..., or about £14,900"); if no dollar amount is left
    in the sentence, the whole sentence goes.
    """
    if not _FOREIGN_AMOUNT.search(text):
        return text
    text = _PARENTHESES.sub(lambda m: "" if _FOREIGN_AMOUNT.search(m.group()) else m.group(), text)
    lines = []
    for line in text.split("\n"):
        kept = []
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            if _FOREIGN_AMOUNT.search(sentence):
                sentence = _CONVERSION.sub("", sentence)
                if not amounts.find(sentence):
                    continue
            kept.append(sentence)
        lines.append(" ".join(kept))
    return ("\n".join(lines).strip() + " " + USD_ONLY).strip()


def restate_listed_prices(text: str, conversation: list[dict], user_messages: list[str]) -> str:
    """Answer a price question about a figure the user suggested earlier, if the model gave no price.

    Someone who named an unlisted price ("$9,995") may later ask for "the price we
    discussed". Models sometimes answer that with a vague refusal; the reply must
    instead say the figure can't be confirmed and repeat the listed prices given before.
    """
    newest = user_messages[-1]
    if ("$" in text or not PRICE_QUESTION.search(newest) or unlisted_amounts([newest])
            or not unlisted_amounts(user_messages[:-1])):
        return text
    given = next((found for m in reversed(conversation[:-1]) if m["role"] == "assistant"
                  and (found := price_sentences(m["content"]))), [])
    if not given:
        return text
    listed = "; ".join(sentence.rstrip(".") for sentence in given)
    return ("I can't confirm that amount: no PlacidWay page lists it. Here is what I gave earlier from the pages: "
            f"{listed}. For a current price, please request a free quote from PlacidWay.")
