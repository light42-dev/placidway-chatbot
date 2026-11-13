"""Dollar amounts: how they are written, and which ones PlacidWay's pages list.

Every check that has to recognise a price reads it through this module, so
"$18,995", "18 995 USD", "$19k", "5 mil dólares" and "50 دولار" are
understood the same way everywhere.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from functools import lru_cache

from .language import detect
from .retrieval import load_index

# "18,995", "18.995" or "18 995": the thousands separator may also be a no-break
# space (\u00a0, \u202f, \u2009) or the Arabic comma (\u066c). \d matches
# Arabic-Indic digits too, and float() reads them.
_GROUPED = r"\d{1,3}(?:[,. \u00a0\u202f\u2009\u066c]\d{3})+(?!\d)"
_DIGITS = rf"(?:{_GROUPED}|\d+(?:\.\d+)?)"
_THOUSANDS = r"\s?(?:k|thousand|grand|mil)\b"
NUMBER = rf"{_DIGITS}(?:{_THOUSANDS})?"       # for other patterns: "18,995", "1.5", "31k"

# A number with what may stand around it. A "$" right after a letter is another
# country's dollar ("C$", "MX$"), so only "US$" counts.
_WRITTEN = re.compile(
    rf"(?P<before>(?:US\s?\$|(?<![A-Za-z])\$|USD\s?)\s?)?"
    rf"(?<![\d,.])(?P<digits>{_DIGITS})(?P<thousands>{_THOUSANDS})?"
    rf"(?P<after>\s?(?:\$(?!\s?\d)|USD\b|US dollars?\b|dollars?\b|d[oó]lar(?:es)?\b|دولار\w*))?",
    re.I)
_SPACE_IN_NUMBER = re.compile(r"(?<=\d)[ \u00a0\u202f\u2009](?=\d{3})")

HIDDEN = {"en": "that amount", "es": "esa cifra", "fr": "ce montant", "ar": "ذلك المبلغ"}


def _value(match: re.Match) -> float:
    digits = match["digits"]
    if re.fullmatch(_GROUPED, digits):
        digits = re.sub(r"\D", "", digits)          # drop the thousands separators
    return float(digits) * (1000 if match["thousands"] else 1)


def _is_money(match: re.Match, shorthand: bool = False) -> bool:
    """True if the number carries a currency sign or word; with `shorthand`, "65k" and "18 grand" count too."""
    return bool(match["before"] or match["after"] or (shorthand and match["thousands"]))


def numbers(text: str) -> set[float]:
    """Every number in the text, money or not ("31k" is 31000)."""
    return {_value(match) for match in _WRITTEN.finditer(text)}


def find(text: str, shorthand: bool = False) -> list[tuple[str, float]]:
    """The dollar amounts in the text, each as (how it is written, its value)."""
    return [(match.group(), _value(match)) for match in _WRITTEN.finditer(text) if _is_money(match, shorthand)]


@lru_cache(maxsize=None)
def listed(page: str | None = None) -> frozenset[float]:
    """The dollar amounts stated on one page (given its key), or on any of the pages."""
    return frozenset(value for passage in load_index().passages if page is None or passage.page == page
                     for _, value in find(passage.text))


def hide(text: str, unwanted: Callable[[float], bool]) -> str:
    """Replace each dollar amount for which `unwanted(value)` is true with "that amount", in the text's language.

    An amount that stays is written with commas ("$18 995" becomes "$18,995"),
    so that nobody reads it as $18.
    """
    placeholder = HIDDEN[detect(text)]

    def swap(match: re.Match) -> str:
        if not _is_money(match):
            return match.group()
        return placeholder if unwanted(_value(match)) else _SPACE_IN_NUMBER.sub(",", match.group())

    text = _WRITTEN.sub(swap, text)
    return re.sub(rf"\b(?:a|an) (?={HIDDEN['en']})", "", text, flags=re.I)       # "a $12,000 fee"
