"""Small fixes applied in code after the model has answered.

The prompt asks for these things, but a model sometimes forgets one, and
each is easy to check in code:
- a "we don't know" reply must point the visitor to a free quote;
- a question about the visitor's own health or safety must end with a
  pointer to their doctor;
- a reply that repeats a passage's wording must cite it, even if the model
  named no passage on its USED line.
"""
from __future__ import annotations

import re

QUOTE_LINE = "You can request a free quote from PlacidWay for details."
DOCTOR_LINE = "Please talk to your doctor about what is right for you."

_UNKNOWN = re.compile(
    r"don['’]?t know|do not know|not sure|(?:don['’]?t|do not|doesn['’]?t|does not) (?:say|list|mention|state)"
    r"|(?:not|isn['’]?t|aren['’]?t) (?:listed|stated|mentioned|specified)", re.I)
_HAS_QUOTE = re.compile(r"quote|contact|reach out|consultation", re.I)
_HEALTH_QUESTION = re.compile(
    r"\bsafe|\brisk|side effect|diabet|heart|afib|blood (?:pressure|thinner)|medication|pregnan"
    r"|my (?:health|condition)|should i (?:do|try|go|take|stop|skip)", re.I)
_HAS_REFERRAL = re.compile(r"doctor|physician|oncologist|medical (?:team|professional|provider)"
                           r"|healthcare (?:team|professional|provider)", re.I)
_WORD = re.compile(r"[a-z0-9$]+")
SHARED_WORDS = 4        # this many words in a row, copied from a passage, count as using it


def add_missing_pointers(text: str, user_message: str) -> str:
    """Append the quote and doctor lines when the reply needs them and lacks them."""
    if _UNKNOWN.search(text) and not _HAS_QUOTE.search(text):
        text += " " + QUOTE_LINE
    if _HEALTH_QUESTION.search(user_message) and not _HAS_REFERRAL.search(text):
        text += " " + DOCTOR_LINE
    return text


def _runs(text: str) -> set[tuple[str, ...]]:
    words = _WORD.findall(text.lower().replace("-", ""))
    return {tuple(words[i:i + SHARED_WORDS]) for i in range(len(words) - SHARED_WORDS + 1)}


def quoted_passage(text: str, passage_texts: list[str]) -> int | None:
    """Index of the first passage the reply copies a run of words from, if any."""
    reply_runs = _runs(text)
    for i, passage in enumerate(passage_texts):
        if reply_runs & _runs(passage):
            return i
    return None
