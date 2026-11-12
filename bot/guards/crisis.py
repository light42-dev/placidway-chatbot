"""Spotting a user who may be thinking of suicide or self-harm, and answering safely.

This is done in code, not left to the model: a crisis reply must always carry
a crisis line and must never quote prices, whatever the model writes.
"""
from __future__ import annotations

import re

# Phrases a person in crisis might use (English and Spanish). Kept broad on purpose:
# a false alarm costs one gentle reply, a miss costs much more.
CRISIS_PATTERN = re.compile(
    r"suicid|kill(ing)? myself|end (it all|my life|things)|take my (own )?life"
    r"|hurt(ing)? myself|self[- ]harm|want(ed)? to die|better off dead|no reason to live"
    r"|(don['’]?t|do not|no longer) want to (be here|be alive|live|go on|wake up)"
    r"|can['’]?t go on|not be here anymore"
    r"|quiero morir|no quiero (vivir|seguir)|quitarme la vida|matarme",
    re.I,
)

CRISIS_PROMPT = """You are the PlacidWay assistant. The user may be thinking of suicide or self-harm. Reply with warmth in the user's language, in under 80 words, plain text:
- Say you are sorry they are carrying this and glad they told you; they don't have to face it alone.
- If they are in the US, they can call or text 988 (Suicide and Crisis Lifeline) any time; if in immediate danger, call emergency services (911).
- Gently ask if someone close could be with them now.
Do not mention prices, treatments, clinics or links. Do not give medical advice."""

CRISIS_LINE = ("If you are in the US, you can call or text 988 to reach the Suicide and Crisis "
               "Lifeline at any time. If you are in immediate danger, please call emergency services (911).")

_HAS_RESOURCE = re.compile(r"\b988\b|\b911\b|emergency services", re.I)
_PRICE_SENTENCE = re.compile(r"[^.!?\n]*(\$|\bUSD\b|\d{1,3},\d{3})[^.!?\n]*[.!?]?", re.I)


def is_crisis(text: str) -> bool:
    return bool(CRISIS_PATTERN.search(text))


def make_crisis_reply_safe(text: str) -> str:
    """Remove any sentence with a price and make sure a crisis line is present."""
    text = _PRICE_SENTENCE.sub("", text).strip()
    if not _HAS_RESOURCE.search(text):
        text = (text + "\n\n" + CRISIS_LINE).strip()
    return text
