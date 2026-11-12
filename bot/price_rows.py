"""Make sure the price-table row for something the user named reaches the model.

Keyword ranking puts a short price table (for example "| Breast Cancer | ... |
$18995 |") below longer passages that say "cost" and "program" many times, so
"what does breast cancer treatment cost" could miss the one row that answers
it. Here, if a user message names the label of a priced table row, the passage
holding that row is put first (second, when the user is on another page), and
the lowest-ranked passages are dropped to stay within the size budget.
"""
from __future__ import annotations

import re

from .config import CONTEXT_CHARS
from .retriever import Passage

# A table row with a label in its first cell and a dollar amount later on.
PRICED_ROW = re.compile(r"^\|\s*([^|\n]+?)\s*\|[^\n]*\$\s?\d", re.M)
# Words too common to identify a row on their own.
GENERIC = {"cancer", "treatment", "therapy", "package", "program", "and", "the", "with"}


def _label_words(label: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", label.lower())) - GENERIC


def find_price_passage(user_messages: list[str], all_passages: list[Passage]) -> Passage | None:
    """The passage with a priced row whose label a user message names, newest message first."""
    for message in reversed(user_messages):
        words = set(re.findall(r"[a-z]+", message.lower()))
        for passage in all_passages:
            for match in PRICED_ROW.finditer(passage.text):
                label = _label_words(match.group(1))
                if label and label <= words:
                    return passage
    return None


def pin_price_rows(passages: list[Passage], user_messages: list[str], all_passages: list[Passage],
                   focus_page: str | None = None, budget_chars: int = CONTEXT_CHARS) -> list[Passage]:
    """Add the matching price-row passage near the top, keeping the total within the budget."""
    pinned = find_price_passage(user_messages, all_passages)
    if pinned is None:
        return passages
    rest = [p for p in passages if p != pinned]
    # The page the user is asking about keeps the top place; it is what the bot should cite.
    position = 1 if rest and focus_page and focus_page != pinned.page and rest[0].page == focus_page else 0
    result = rest[:position] + [pinned] + rest[position:]
    while len(result) > 1 and sum(len(p.text) for p in result) > budget_chars:
        result.pop()
    return result
