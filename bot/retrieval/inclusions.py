"""Make sure a package's "Included in ..." sections reach the model when the user asks what is included.

Keyword ranking misses them on a full question such as "What is included in
the alternative adenocarcinoma cancer treatment package?": the sections that
list the inclusions say "included" once in their heading and never repeat the
words "adenocarcinoma", "treatment" or "package", so passages that do repeat
them (costs, FAQs, optional extras) fill the size budget first. Here, when
the newest message asks what is included, the "Included in ..." passages of
the page under discussion are put first, and the lowest-ranked passages are
dropped to stay within the size budget.
"""
from __future__ import annotations

import re

from ..config import CONTEXT_CHARS
from .index import Passage, tokenize

# A passage whose heading (its first line) reads "# Included in the Out-Patient Program ...".
INCLUDED_HEADING = re.compile(r"^# [^\n]*\bincluded in\b", re.I)
# Stems of "include", "includes", "included", "including" and "inclusion(s)"; Spanish and
# Arabic forms have already been mapped to these by tokenize().
INCLUSION_STEMS = {"includ", "inclusion"}


def asks_what_is_included(message: str) -> bool:
    return bool(INCLUSION_STEMS & set(tokenize(message)))


def pin_inclusions(passages: list[Passage], question: str, all_passages: list[Passage],
                   focus_page: str | None, budget_chars: int = CONTEXT_CHARS) -> list[Passage]:
    """Put the focus page's "Included in ..." passages first, keeping the total within the budget."""
    if not focus_page or not asks_what_is_included(question):
        return passages
    pinned = [p for p in all_passages if p.page == focus_page and INCLUDED_HEADING.match(p.text)]
    if not pinned:
        return passages
    result = pinned + [p for p in passages if p not in pinned]
    while len(result) > len(pinned) and sum(len(p.text) for p in result) > budget_chars:
        result.pop()
    return result
