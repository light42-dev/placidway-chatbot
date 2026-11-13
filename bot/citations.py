"""Turn the model's "USED: 1, 3" line into a Source line of real page URLs.

The model only points at passages; the URLs come from our own page list, so
a link can never be invented or mistyped. If the model names no passage but
clearly used one, the passage is worked out from the reply itself.
"""
from __future__ import annotations

import re

from .history import MONEY, PLACIDWAY_URL, SOURCE_LINE
from .pages import PAGE_BY_KEY
from .retrieval import Passage

USED_LINE = re.compile(r"\n?\s*USED:\s*([^\n]*)\s*$", re.I)
# Passage markers some models write inside the text instead: "【2】", "【2†L1-L3】", "[2]".
MARKER = re.compile(r"\s*(?:【\s*(\d+)[^】]*】|\[(\d+)\])")
SHARED_WORDS = 4        # this many words in a row, copied from a passage, count as using it
_WORD = re.compile(r"[a-z0-9$]+")
_FIGURE = re.compile(r"\d[\d,]*\d|\d")


def split_used_line(reply: str) -> tuple[str, list[int]]:
    """(the reply without its USED line, links or Source line; the passage numbers it named)."""
    used = USED_LINE.search(reply)
    numbers = [int(n) for n in re.findall(r"\d+", used.group(1))] if used else []
    text = SOURCE_LINE.sub("", USED_LINE.sub("", reply))
    numbers += [int(a or b) for a, b in MARKER.findall(text) if int(a or b) not in numbers]
    text = MARKER.sub("", text)
    return PLACIDWAY_URL.sub("", text).strip(), numbers      # drop any URL the model typed itself


def _word_runs(text: str) -> set[tuple[str, ...]]:
    words = _WORD.findall(text.lower().replace("-", ""))
    return {tuple(words[i:i + SHARED_WORDS]) for i in range(len(words) - SHARED_WORDS + 1)}


def _passage_used(text: str, passages: list[Passage]) -> Passage | None:
    """Best guess at the passage behind a reply that named none.

    In order: a passage the reply copies a run of words from; a passage
    holding one of the reply's figures; the top passage, if a price is stated.
    """
    reply_runs = _word_runs(text)
    for passage in passages:
        if reply_runs & _word_runs(passage.text):
            return passage
    figures = set(_FIGURE.findall(text))
    for passage in passages:
        if any(re.search(rf"(?<![\d,]){re.escape(figure)}(?![\d,])", passage.text) for figure in figures):
            return passage
    return passages[0] if MONEY.search(text) else None


def cite(text: str, numbers: list[int], passages: list[Passage]) -> tuple[str, list[str]]:
    """Append "Source: <urls>" for the passages used. Returns (reply, urls)."""
    used = [passages[n - 1] for n in numbers if 1 <= n <= len(passages)]
    if not used and passages:
        guessed = _passage_used(text, passages)
        used = [guessed] if guessed else []
    urls = list(dict.fromkeys(PAGE_BY_KEY[passage.page].url for passage in used))
    if urls:
        text += "\n\nSource: " + " , ".join(urls)
    return text, urls
