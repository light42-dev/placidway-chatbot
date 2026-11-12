"""Noticing when the user has moved on to a new subject.

The focus page (see retriever.find_focus_page) is the page whose topic word the
user wrote most recently. It keeps follow-ups such as "and the inpatient one?"
on the same package. But after "Forget that. What's the cheapest ozone therapy
you list", the old focus would keep pulling the anal cancer package to the top
and push out the passages that answer the new question.

So the focus is dropped when the newest message, on its own, asks about a word
the focus page never uses and matches another page clearly better.
"""
from __future__ import annotations

from functools import lru_cache

from .retriever import SYNONYM_STEMS, Index, expand, find_focus_page, tokenize

SHIFT_RATIO = 1.5   # another page must match the newest message this much better than the focus page
GENERIC = frozenset().union(*SYNONYM_STEMS)   # question words such as "much" or "include" mark no new subject


@lru_cache(maxsize=None)
def _page_terms(index: Index, page: str) -> frozenset[str]:
    return frozenset(term for passage, counts in zip(index.passages, index.term_counts)
                     if passage.page == page for term in counts)


def topic_shifted(message: str, focus_page: str, index: Index) -> bool:
    """True if the newest message is about something the focus page does not cover."""
    if find_focus_page([message], None) == focus_page:
        return False                    # the user named the focus page's topic again
    terms = {term for term in tokenize(message) if term in index.idf}
    new_words = {term for term in terms - _page_terms(index, focus_page) - GENERIC
                 if sum(term in counts for counts in index.term_counts) >= 2}   # skip one-off words
    if not new_words:
        return False                    # the question uses no subject word the focus page lacks
    query = {term: weight for term, weight in expand(terms).items() if term in index.idf}
    best_focus = best_other = 0.0
    for i, passage in enumerate(index.passages):
        score = index._score(i, query)
        if passage.page == focus_page:
            best_focus = max(best_focus, score)
        else:
            best_other = max(best_other, score)
    return best_other >= SHIFT_RATIO * best_focus


def current_focus(user_messages: list[str], last_cited: str | None, index: Index) -> str | None:
    """The focus page for this turn, or None when the user has changed the subject."""
    focus = find_focus_page(user_messages, last_cited)
    if focus and user_messages and topic_shifted(user_messages[-1], focus, index):
        return None
    return focus
