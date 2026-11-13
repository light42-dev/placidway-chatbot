"""Decide which page a conversation is about (the "focus page").

Passages from the focus page are ranked higher, which keeps a follow-up such
as "and the inpatient one?" on the package being discussed. The focus is, in
order:

1. the page whose topic word the newest message uses ("adrenal", "videos");
2. the clinic profile, if the newest message asks about the clinic itself
   (its founder, doctors, location);
3. the page an older message named, or the page the user goes back to
   ("back to the first treatment I asked about");
4. the page the bot cited last.

When the user says they are changing the subject ("forget that", "different
question"), nothing is inherited: that turn has no focus, and later turns do
not look past it for a page named earlier.
"""
from __future__ import annotations

import re

from ..pages import CLINIC_PAGE, CLINIC_TOPICS, COMPARISON_PAGE, PAGES
from .index import search_text

CHANGE_OF_SUBJECT = re.compile(
    r"\bforget (that|it|about)\b|\b(different|another|new|unrelated|separate|random) (question|request|topic|subject|thing)\b"
    r"|\bunrelated\b|\brandom\b|\bsomething else\b|\bchang(e|ing) (the )?(subject|topic)\b|\bautre chose\b|\botra cosa\b",
    re.I)

BACK_REFERENCE = re.compile(
    r"\b(back to|go(ing)? back|return(ing)? to)\b"
    r"|\b(first|original|earlier|previous)\b[^.?!]{0,30}\b(asked|mentioned|discussed|one|treatment|question|topic)\b",
    re.I)
TO_THE_FIRST = re.compile(r"\b(first|original)\b", re.I)
ITC_WORDS = re.compile(r"\b(cancer|tumou?r|itc\b|immunity therapy|tijuana)", re.I)


def _matches(topics: tuple[str, ...], text: str) -> bool:
    return any(re.search(rf"\b{topic}", text) for topic in topics)


def named_page(message: str) -> str | None:
    """The page whose topic word the message uses, if any."""
    text = search_text(message)
    return next((page.key for page in PAGES if _matches(page.topics, text)), None)


def _recalled_page(user_messages: list[str]) -> str | None:
    """The page the newest of these messages goes back to, if it refers back at all.

    "the first / original ..." means the first page discussed; "back to /
    earlier / previous" means the page discussed before the current one.
    """
    if not BACK_REFERENCE.search(search_text(user_messages[-1])):
        return None
    pages: list[str] = []       # pages in the order the user first raised them
    for message in user_messages[:-1]:
        page = named_page(message)
        if page and page not in pages:
            pages.append(page)
    if not pages:
        return None
    if TO_THE_FIRST.search(search_text(user_messages[-1])) or len(pages) == 1:
        return pages[0]
    return pages[-2]


def focus_page(user_messages: list[str], last_cited: str | None) -> str | None:
    """The page this turn is about, or None when the subject is new or unknown."""
    if not user_messages:
        return last_cited
    newest = user_messages[-1]

    decided_now = named_page(newest) or _recalled_page(user_messages)
    if not decided_now and _matches(CLINIC_TOPICS, search_text(newest)):
        decided_now = CLINIC_PAGE
    if decided_now:
        return decided_now
    if CHANGE_OF_SUBJECT.search(newest):
        return None

    inherited = last_cited
    for end in range(len(user_messages) - 1, 0, -1):         # older messages, newest first
        if CHANGE_OF_SUBJECT.search(user_messages[end - 1]):
            break                   # whatever was named before that message is no longer the subject
        page = named_page(user_messages[end - 1]) or _recalled_page(user_messages[:end])
        if page:
            inherited = page
            break
    if inherited == COMPARISON_PAGE and ITC_WORDS.search(newest):
        return CLINIC_PAGE          # a new question about ITC's own care leaves the other-clinics page
    return inherited
