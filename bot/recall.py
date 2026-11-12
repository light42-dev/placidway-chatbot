"""Follow-ups that go back to an earlier subject ("back to the first treatment I asked about").

find_focus_page picks the newest page a user named, which is wrong when the
user explicitly returns to an older one. This module spots such a
back-reference and picks the page it points at.
"""
from __future__ import annotations

import re

from .retriever import find_focus_page

BACK_REFERENCE = re.compile(
    r"\b(back to|go(ing)? back|return(ing)? to)\b"
    r"|\b(first|original|earlier|previous)\b[^.?!]{0,30}\b(asked|mentioned|discussed|one|treatment|question|topic)\b",
    re.I)
TO_THE_FIRST = re.compile(r"\b(first|original)\b", re.I)


def _recalled_page(user_messages: list[str]) -> str | None:
    """The page the newest message refers back to, or None if it refers back to nothing.

    "the first / original ..." means the first page discussed; "back to /
    earlier / previous" means the page discussed before the current one.
    """
    if not BACK_REFERENCE.search(user_messages[-1]):
        return None
    pages: list[str] = []       # pages in the order the user first raised them
    for message in user_messages[:-1]:
        page = find_focus_page([message], None)
        if page and page not in pages:
            pages.append(page)
    if not pages:
        return None
    if TO_THE_FIRST.search(user_messages[-1]) or len(pages) == 1:
        return pages[0]
    return pages[-2]


def focus_page(user_messages: list[str], last_cited: str | None) -> str | None:
    """Like find_focus_page, but a message that goes back to an earlier subject sets the focus too.

    Messages are read newest first: the first one that names a page, or
    refers back to one, decides. Otherwise the page cited last is kept.
    """
    for end in range(len(user_messages), 0, -1):
        page = find_focus_page([user_messages[end - 1]], None) or _recalled_page(user_messages[:end])
        if page:
            return page
    return last_cited
