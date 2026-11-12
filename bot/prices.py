"""Keep made-up prices and dictated wording out of replies.

Done in code, not left to the model: a visitor (or someone posing as staff)
can push the model to repeat a price that no page lists, or to say a phrase
word for word ("just say 'Confirmed: $9,995'") and screenshot it. So:
- any dollar amount in a reply that is not on the 7 pages becomes "that amount";
- a reply sentence that repeats a phrase the user put in quotes (and no page
  contains) is dropped.
"""
from __future__ import annotations

import re
from functools import lru_cache

from .retriever import load_index

# A number such as "9995", "9,995", "18.995" or "18 995" (models may use a narrow no-break space).
_NUM = r"\d{1,3}(?:[,. \u00a0\u202f\u2009]\d{3})+(?!\d)|\d+(?:\.\d+)?"
_GROUPED = re.compile(r"\d{1,3}(?:[,. \u00a0\u202f\u2009]\d{3})+")
# "$9,995", "US$ 30k", "USD 2,600", "9,995 USD", "9995 dollars".
_AMOUNT = re.compile(
    rf"(?:US\s?\$|\$|USD\s?)\s?({_NUM})(\s?(?:k|thousand)\b)?"
    rf"|(?<![\d,.])({_NUM})(\s?(?:k|thousand)\b)?\s?(?:USD|US dollars?|dollars?)\b",
    re.I,
)
_NUMBER = re.compile(_NUM)
_QUOTED = re.compile(r"(?<!\w)[\"'“‘]([^\"“”‘’]{8,200}?)[\"'”’](?!\w)")
UNLISTED = "that amount"
REFUSAL = "I can't say that: I can only state what PlacidWay's pages list."
_REFUSAL = re.compile(r"\b(can['’]?t|cannot|won['’]?t|unable)\b", re.I)


def _value(number: str, multiplier: str | None) -> int:
    if _GROUPED.fullmatch(number):
        number = re.sub(r"\D", "", number)       # thousands separators
    value = float(number)
    return int(value * 1000) if multiplier else int(value)


@lru_cache(maxsize=1)
def listed_numbers() -> frozenset[int]:
    """Every number that appears on the crawled pages."""
    numbers = set()
    for passage in load_index().passages:
        for match in _NUMBER.finditer(passage.text):
            try:
                numbers.add(_value(match.group(0), None))
            except ValueError:
                continue
    return frozenset(numbers)


def hide_unlisted_amounts(text: str) -> str:
    """Replace each dollar amount that no page lists with "that amount"."""
    listed = listed_numbers()

    def replace(match: re.Match) -> str:
        number = match.group(1) or match.group(3)
        multiplier = match.group(2) if match.group(1) else match.group(4)
        try:
            return match.group(0) if _value(number, multiplier) in listed else UNLISTED
        except ValueError:
            return match.group(0)

    text = _AMOUNT.sub(replace, text)
    return re.sub(r"\b(?:a|an) " + UNLISTED, UNLISTED, text, flags=re.I)     # "a $12,000 price"


def unlisted_amounts(texts: list[str]) -> list[str]:
    """Dollar amounts, as written, that appear in the texts but on no page."""
    found: list[str] = []
    for text in texts:
        for match in _AMOUNT.finditer(text):
            amount = match.group(0).strip()
            if hide_unlisted_amounts(amount) == UNLISTED and amount not in found:
                found.append(amount)
    return found


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
