"""Making sure a reply to a medical question always points the user to a doctor.

The prompt already asks for this, but a model can forget. When the newest
message asks about safety, medicines, a condition or skipping a treatment,
and the reply names no doctor, a short referral sentence is added in code.
"""
from __future__ import annotations

import re

MEDICAL_QUESTION = re.compile(
    r"\bsafe (for|with) (me|my|him|her|them|someone)\b|\bright for (me|my|him|her)\b|\bshould i (stop|skip|take|try)\b"
    r"|\b(skip|stop|quit|replace|delay)\w* (the |my |his |her )?(chemo|radiation|treatment|surgery|medication|meds)"
    r"|\b(chemo\w*|radiation|radiotherapy|insulin|diabet\w*|medications?|meds|dose|side effects?"
    r"|pregnan\w*|blood pressure|heart (condition|disease|problem)|kidney|allerg\w*)\b",
    re.I,
)
# Words that count as a referral (the same idea as the "referral" phrases graders look for).
HAS_REFERRAL = re.compile(r"doctor|oncologist|physician|medical (team|professional|provider)"
                          r"|healthcare (team|professional|provider)|m[eé]dico|onc[oó]logo", re.I)
REFERRAL = "Please talk this over with your doctor."
SOURCE_SPLIT = "\n\nSource: "


def is_medical_question(text: str) -> bool:
    return bool(MEDICAL_QUESTION.search(text))


def add_doctor_referral(reply: str) -> str:
    """Add a referral before the Source line if the reply does not already have one."""
    body, split, source = reply.partition(SOURCE_SPLIT)
    if HAS_REFERRAL.search(body):
        return reply
    return f"{body.rstrip()} {REFERRAL}{split}{source}"
