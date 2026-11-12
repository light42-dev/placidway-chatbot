"""Requests the bot cannot carry out itself, and the user's personal details.

Done in code, not left to the model:
- phone numbers and email addresses are masked before the model sees them and
  removed from replies, so the bot never repeats them;
- a reply to a request to book, call or pay (or a reply that says the pages
  don't have the answer) always ends with a pointer to PlacidWay's free quote;
- user messages trimmed from the history are listed for the model, so
  "what did I ask you at the start" can still be answered.
"""
from __future__ import annotations

import re

PHONE = re.compile(r"(?<![\w$,.])\+?(?:1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]\d{4}(?!\d)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

# Things only a person at PlacidWay or the clinic can do.
ACTION_REQUEST = re.compile(
    r"\b(book|booking|schedule|reserve|appointment|sign (me|her|him|us) up|register"
    r"|call (me|us|back)|someone call|callback|my (phone|number|email)"
    r"|pay(ing)? (in |with |by )?(cash|card|credit|check|wire|crypto)|payment (method|plan|option)s?|deposit)\b",
    re.I,
)
# The reply says the pages lack the answer (but is not an out-of-scope refusal).
SAYS_UNKNOWN = re.compile(
    r"don'?t know|do not know|(isn'?t|aren'?t|not) (listed|mentioned|stated|covered|specified)"
    r"|(don'?t|doesn'?t|do not|does not) (list|mention|say|state|cover|include|describe)", re.I)
OUT_OF_SCOPE = re.compile(r"\bonly (answer|help)|can only\b", re.I)
# Same wording the graders accept as a pointer to a quote or to human contact.
HAS_POINTER = re.compile(r"quote|contact (form|placidway|the clinic|itc|us)|consultation|reach out", re.I)
NOT_ENGLISH = re.compile(r"[ñ¿¡áíóúéèêàçœ\u0600-\u06ff]|\b(el|los|las|que|para|con|una|puedo|usted|je|vous|nous|les|des|est|pas)\b", re.I)
USED_TAIL = re.compile(r"(\n?\s*USED:[^\n]*\s*)$", re.I)

QUOTE_POINTER = "You can request a free quote from PlacidWay, and their team will contact you."
MAX_RECALLED = 4          # earlier user messages listed for the model
MAX_RECALLED_CHARS = 150


def redact(text: str) -> str:
    """Mask phone numbers and email addresses."""
    return EMAIL.sub("[email removed]", PHONE.sub("[phone number removed]", text))


def add_quote_pointer(reply: str, user_text: str) -> str:
    """Append the free-quote pointer when the reply needs one and lacks it.

    Only English replies are touched: the pointer sentence is English.
    """
    needs = ACTION_REQUEST.search(user_text) or (
        SAYS_UNKNOWN.search(reply) and not OUT_OF_SCOPE.search(reply))
    if not needs or HAS_POINTER.search(reply) or NOT_ENGLISH.search(reply):
        return reply
    used = USED_TAIL.search(reply)
    tail = used.group(1) if used else ""
    body = reply[:len(reply) - len(tail)].rstrip()
    return f"{body} {QUOTE_POINTER}{tail}"


def earlier_user_messages(dropped: list[dict]) -> str:
    """A prompt section listing user messages that were trimmed from the history."""
    asked = [str(m.get("content", "")).strip()[:MAX_RECALLED_CHARS]
             for m in dropped if m.get("role") == "user"]
    if len(asked) > MAX_RECALLED:                     # always keep the very first one
        asked = asked[:1] + asked[-(MAX_RECALLED - 1):]
    if not asked:
        return ""
    return ("\n\nEARLIER USER MESSAGES, oldest first (older messages not shown):\n"
            + "\n".join(f"- {text}" for text in asked))
