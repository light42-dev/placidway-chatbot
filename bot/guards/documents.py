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

from .. import amounts

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

FIGURE_REFUSAL = "I can't present your figure as a price: it isn't listed on PlacidWay's pages."

FIGURE_RULE = ("\n\nThe user's figure {figures} is on none of PlacidWay's pages. Say you can't use it because "
               "it isn't listed, never show it as a price (not in a table either), and give the listed price "
               "for the subject discussed.")


def unlisted_figures(question: str) -> list[float]:
    """Dollar figures in the user's message that no page lists, shorthand such as "65k" included.

    A bare number (a date, "5-star") is ignored.
    """
    values = [value for _, value in amounts.find(question, shorthand=True) if value not in amounts.listed()]
    return list(dict.fromkeys(values))          # each one once


def is_document_request(question: str) -> bool:
    return bool(_DOCUMENT.search(question) or _CONFIRM_OWN.search(question))


def _figures_to_refuse(question: str) -> list[float]:
    """Unlisted figures the user wants written up or published (not, say, a budget they mention)."""
    if is_document_request(question) or _PRESENT.search(question):
        return unlisted_figures(question)
    return []


def extra_rules(question: str) -> str:
    """Prompt text for this message only; empty for ordinary questions."""
    text = DOCUMENT_RULE if is_document_request(question) else ""
    figures = _figures_to_refuse(question)
    if figures:
        text += FIGURE_RULE.format(figures=", ".join(f"${value:,.0f}" for value in figures))
    return text


def make_safe(question: str, text: str, sources: list[str]) -> tuple[str, list[str]]:
    """Make sure the reply refuses what it must, whatever the model wrote."""
    if is_document_request(question):
        if _DOCUMENT_TEXT.search(text) or not _DECLINED.search(text):
            return REFUSAL, []          # the model wrote (part of) the document, or did not refuse
    figures = set(_figures_to_refuse(question))
    if figures:
        # Drop table rows that would present the user's figure as a price.
        lines = [line for line in text.split("\n")
                 if not (line.lstrip().startswith("|") and amounts.numbers(line) & figures)]
        text = "\n".join(lines)
        if not _DECLINED.search(text):
            text = FIGURE_REFUSAL + "\n\n" + text
    return text, sources
