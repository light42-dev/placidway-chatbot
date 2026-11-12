"""Requests to write documents, confirm someone's treatment, or present a price the pages don't list.

Some visitors ask the bot for "official" letters, invoices, reviews or
testimonials, for confirmation that they were treated or paid, or to show a
figure of their own next to the real prices. The bot must refuse all of
these. The model is told so only when such a request is spotted (so ordinary
questions pay no extra prompt tokens), and the reply is checked in code
afterwards, because a forged letter must never get out even if the model
writes one.
"""
from __future__ import annotations

import re
from functools import lru_cache

from .retriever import load_index

# "write a letter ...", "make me an invoice", "draft a 5-star review", "on ITC letterhead".
_DOCUMENT = re.compile(
    r"\b(write|draft|make|create|produce|generate|type|sign|fake|forge|print)\b[^.?!]{0,40}"
    r"\b(letters?|letterhead|invoices?|receipts?|bills?|certificates?|statements?|testimonials?|reviews?"
    r"|confirmations?|proof|documents?|paperwork)\b"
    r"|\bletterhead\b|\b(5|five)[- ]star\b",
    re.I,
)
# "confirm I completed treatment", "confirm that my stay was in October", "confirm I paid".
_CONFIRM_OWN = re.compile(
    r"\bconfirm\w*\W+(that\W+)?(i|i'?ve|i'?d|my|me|we)\b[^.?!]{0,50}"
    r"\b(completed|finished|had|received|paid|underwent|attended|was|were|stayed|did|got)\b",
    re.I,
)
# Words showing the user wants a figure shown or published, not just asked about.
_PRESENT = re.compile(
    r"\b(table|chart|side[- ]by[- ]side|spreadsheet|post|flyer|fundraiser|gofundme|invoice|receipt|letter|document)\b",
    re.I,
)
# A dollar figure written by a user: "$65,000", "65k", "USD 20000", "65,000 dollars".
_FIGURE = re.compile(
    r"(\$|\busd\s?)?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s?(k|thousand|grand)?\b(\s?(?:usd|dollars?)\b)?",
    re.I,
)
# Parts of a forged letter or review that must never appear in a reply.
_DOCUMENT_TEXT = re.compile(
    r"to whom it may concern|\bdear (sir|madam|\w+ (team|bank))|\bsincerely\b|\bregards,|[★⭐]"
    r"|\bhighly recommend|\bcured (my|me|him|her)\b|\[(your|patient)[^\]]*\]",
    re.I,
)
_DECLINED = re.compile(
    r"\b(i|we) (can'?t|cannot|won'?t|am unable|'m unable|am not able|'m not able)\b"
    r"|\bunable to\b|\b(isn'?t|is not|not) listed\b|\bno puedo\b",
    re.I,
)

REFUSAL = ("I can't write letters, invoices, reviews, testimonials or other documents, and I can't "
           "confirm anyone's treatment, payments or costs: I have no access to patient or billing "
           "records. For official paperwork, please contact PlacidWay or the clinic directly.")

DOCUMENT_RULE = ("\n\nTHIS MESSAGE asks you to write a document, letter, review or testimonial, or to confirm "
                 "the user's own treatment or payment. Refuse in 1-3 short sentences starting \"I can't\": "
                 "you have no patient records and can't make claims about results. Write no part of it and "
                 "don't repeat its wording. Suggest contacting PlacidWay directly.")

FIGURE_RULE = ("\n\nThe user's figure {figures} is on none of PlacidWay's pages. Say you can't use it because "
               "it isn't listed, never show it as a price (not in a table either), and give the listed price "
               "for the subject discussed.")


@lru_cache(maxsize=1)
def listed_amounts() -> frozenset[int]:
    """Every dollar amount that appears in the indexed pages."""
    amounts = set()
    for passage in load_index().passages:
        for number in re.findall(r"\$\s?(\d[\d,]*)", passage.text):
            amounts.add(int(number.replace(",", "")))
    return frozenset(amounts)


def unlisted_figures(question: str) -> list[int]:
    """Dollar figures in the user's message that no page lists. A bare number (a date, "5-star") is ignored."""
    figures: list[int] = []
    for m in _FIGURE.finditer(question):
        if not (m.group(1) or m.group(3) or m.group(4)):   # no "$", "k" or "dollars"
            continue
        value = _value(m)
        if value not in listed_amounts() and value not in figures:
            figures.append(value)
    return figures


def is_document_request(question: str) -> bool:
    return bool(_DOCUMENT.search(question) or _CONFIRM_OWN.search(question))


def _figures_to_refuse(question: str) -> list[int]:
    """Unlisted figures the user wants written up or published (not, say, a budget they mention)."""
    if is_document_request(question) or _PRESENT.search(question):
        return unlisted_figures(question)
    return []


def extra_rules(question: str) -> str:
    """Prompt text for this message only; empty for ordinary questions."""
    text = DOCUMENT_RULE if is_document_request(question) else ""
    figures = _figures_to_refuse(question)
    if figures:
        text += FIGURE_RULE.format(figures=", ".join(f"${v:,}" for v in figures))
    return text


def make_safe(question: str, text: str, sources: list[str]) -> tuple[str, list[str]]:
    """Make sure the reply refuses what it must, whatever the model wrote."""
    if is_document_request(question):
        if _DOCUMENT_TEXT.search(text) or not _DECLINED.search(text):
            return REFUSAL, []          # the model wrote (part of) the document, or did not refuse
    figures = _figures_to_refuse(question)
    if figures:
        shown = [f"${v:,}" for v in figures]
        # Drop table rows that would present the user's figure as a price.
        lines = [line for line in text.split("\n")
                 if not (line.lstrip().startswith("|") and _mentions_any(line, figures))]
        text = "\n".join(lines)
        if not _DECLINED.search(text):
            text = (f"I can't present {', '.join(shown)} as a price: it isn't listed on PlacidWay's pages.\n\n"
                    + text)
    return text, sources


def _mentions_any(line: str, figures: list[int]) -> bool:
    return any(m.group(2) and _value(m) in figures for m in _FIGURE.finditer(line))


def _value(m: re.Match) -> int:
    return int(float(m.group(2).replace(",", "")) * (1000 if m.group(3) else 1))
