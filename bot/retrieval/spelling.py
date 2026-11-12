"""Forgiving search for misspelled question words.

Visitors type fast and misspell ("PROSTRATE" for "prostate"). A query word
that appears in no passage would score nothing, so it is replaced by the most
similar word that does appear, if one is close enough. Short words are left
alone: they are too easy to "correct" into something else.
"""
from __future__ import annotations

import difflib

MIN_LENGTH = 5          # words shorter than this are never corrected
CUTOFF = 0.85           # how similar (0..1) a known word must be to stand in


def correct(term: str, vocabulary) -> str | None:
    """The known word closest to `term`, or None if no word is close enough."""
    if len(term) < MIN_LENGTH or not term.isalpha():
        return None
    matches = difflib.get_close_matches(term, vocabulary, n=1, cutoff=CUTOFF)
    return matches[0] if matches else None
