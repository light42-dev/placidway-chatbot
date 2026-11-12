"""Make sure a reply points the visitor to the right next step.

The prompt asks for both of these, but a model sometimes forgets, and each is
easy to check in code:

- a reply that says the pages lack the answer, or a request only a person can
  carry out (booking, a call back, payment), ends with a pointer to
  PlacidWay's free quote;
- a reply to a question about the visitor's own health names their doctor.
"""
from __future__ import annotations

import re

from ..language import detect

# The reply says the pages do not have the answer ...
SAYS_UNKNOWN = re.compile(
    r"don'?t know|do not know|not sure|(can'?t|cannot) find|\bno (information|details|mention|data)\b"
    r"|\b(don'?t|do not|doesn'?t|does not) (have|list|mention|say|state|include|cover|describe|give|provide|publish)"
    r"|\b(not|isn'?t|aren'?t) (listed|stated|mentioned|described|covered|included|specified|available|provided|published)"
    r"|no (lo )?s[eé]\b|no (aparece|figura|se menciona)|je ne sais pas|ne figure(nt)? pas|لا [أا]عرف|غير (مذكور|مدرج)",
    re.I)
# ... but is not simply declining an off-topic question, which needs no quote.
OUT_OF_SCOPE = re.compile(r"\bcan only\b|\bonly (answer|help)\b|s[oó]lo puedo|ne peux (que|répondre qu)", re.I)
# Things only a person at PlacidWay or the clinic can do.
ACTION_REQUEST = re.compile(
    r"\b(book|booking|schedule|reserve|appointment|sign (me|her|him|us) up|register"
    r"|call (me|us|back)|someone call|callback|my (phone|number|email)"
    r"|pay(ing)? (in |with |by )?(cash|card|credit|check|wire|crypto)|payment (method|plan|option)s?|deposit)\b",
    re.I)
# The reply already points to a quote or to a person (the wording the test suite accepts).
HAS_QUOTE_POINTER = re.compile(
    r"quote|contact (form|placidway|the clinic|itc|us)|consultation|reach out"
    r"|cotizaci[oó]n|presupuesto|contact(ar|e)\b|devis|contacter|عرض (سعر|[أا]سعار)|تواصل", re.I)
QUOTE_POINTER = {
    "en": "You can request a free quote from PlacidWay, and their team will contact you.",
    "es": "Puede solicitar una cotización gratuita a PlacidWay y su equipo le contactará.",
    "fr": "Vous pouvez demander un devis gratuit à PlacidWay, et leur équipe vous contactera.",
    "ar": "يمكنك طلب عرض سعر مجاني من PlacidWay وسيتواصل معك فريقهم.",
}

# The visitor asks about their own health, safety or medicines.
MEDICAL_QUESTION = re.compile(
    r"\bsafe\b|\brisk|\bright for (me|my|him|her)\b|\bshould i (do|try|go|take|stop|skip)\b|my (health|condition)"
    r"|\b(skip|stop|quit|replace|delay)\w* (the |my |his |her )?(chemo|radiation|treatment|surgery|medication|meds)"
    r"|\b(chemo\w*|radiation|radiotherapy|insulin|diabet\w*|afib|medications?|meds|dose|side effects?"
    r"|pregnan\w*|blood (pressure|thinner)|heart|kidney|allerg\w*)\b"
    r"|presi[oó]n|medicamento|embaraz|quimio",
    re.I)
HAS_DOCTOR_POINTER = re.compile(
    r"doctor|oncologist|physician|(medical|healthcare) (team|professional|provider)"
    r"|m[eé]dico|onc[oó]logo|m[eé]decin|طبيب", re.I)
DOCTOR_POINTER = {
    "en": "Please talk to your doctor about what is right for you.",
    "es": "Por favor, consulte a su médico sobre lo que es adecuado para usted.",
    "fr": "Veuillez en parler à votre médecin.",
    "ar": "يرجى استشارة طبيبك لمعرفة ما يناسبك.",
}


def add_quote_pointer(reply: str, question: str) -> str:
    """Append the free-quote sentence, in the reply's language, when the reply needs one and lacks it."""
    plain = reply.replace("’", "'")
    needed = ACTION_REQUEST.search(question) or (SAYS_UNKNOWN.search(plain) and not OUT_OF_SCOPE.search(plain))
    if not needed or HAS_QUOTE_POINTER.search(reply):
        return reply
    return f"{reply.rstrip()} {QUOTE_POINTER[detect(reply)]}"


def add_doctor_pointer(reply: str, question: str) -> str:
    """Append a doctor referral, in the reply's language, to an answer about the visitor's own health."""
    if not MEDICAL_QUESTION.search(question) or HAS_DOCTOR_POINTER.search(reply):
        return reply
    return f"{reply.rstrip()} {DOCTOR_POINTER[detect(reply)]}"
