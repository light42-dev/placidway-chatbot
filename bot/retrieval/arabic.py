"""English search words for questions written in Arabic.

The index and the page topic words are English, so an Arabic question such as
"هل العلاج بالأوزون أرخص في تركيا؟" would match nothing. `with_glosses` adds
the English words for the Arabic terms it recognises ("ozone cheaper in
turkey"). Only retrieval sees the glosses; the model still gets the user's
own words and replies in their language.

Patterns match inside words, so prefixes such as ال (the), ب (with), ل (for)
and و (and) need no special handling.
"""
from __future__ import annotations

import re

# Arabic letters that are often written in more than one way.
_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ـ": None})
_DIACRITICS = re.compile(r"[ً-ْ]")
_ARABIC = re.compile(r"[؀-ۿ]")

# (pattern on folded Arabic text, English words). Grouped by subject.
GLOSSES = [
    # cost and programs
    (r"تكلف|كلف", "cost price"), (r"سعر|اسعار", "price cost"), (r"\bكم\b", "how much"),
    (r"دولار", "dollar"), (r"متوسط", "average"), (r"ارخص\s+(في|ب)", "cheaper in"),
    (r"ارخص|اقل تكلف|اغلي", "cheaper"), (r"مقارن|قارن", "compare"),
    (r"برنامج|باق", "program package"), (r"داخلي|اقام", "inpatient stay"),
    (r"خارجي", "outpatient"), (r"يشمل|تشمل|يتضمن|تتضمن|شامل", "include"),
    (r"اضافي", "additional extra"), (r"مد[هة]|اسبوع|اسابيع", "weeks duration"),
    # conditions and treatments
    (r"سرطان|اورام", "cancer"), (r"غدي|غدد", "adenocarcinoma"), (r"رئ[هةو]|الرئ", "lung"),
    (r"كظر", "adrenal"), (r"شرج", "anal"), (r"اوزون", "ozone"), (r"مناع", "immunotherapy immune"),
    (r"كيم[يا]", "chemotherapy"), (r"خلايا جذعي", "stem cell"), (r"علاج", "treatment therapy"),
    (r"طبيب|اطباء|دكتور", "doctor"), (r"نتائج|نجاح", "results success"),
    # places
    (r"تيخوانا", "tijuana"), (r"مكسيك", "mexico"), (r"تركيا", "turkey"), (r"اسطنبول", "istanbul"),
    (r"المانيا", "germany"), (r"تايلاند", "thailand"), (r"هند\b", "india"),
    # travel and visit
    (r"فندق|سكن", "hotel accommodation"), (r"وجب|طعام|اكل", "meal food"),
    (r"مطار|طيران|سفر", "airport flight travel"), (r"نقل|مواصلات", "transport"),
    (r"تاشير", "visa"), (r"حجز|احجز", "book"), (r"موعد|مواعيد", "appointment"),
    (r"فيديو", "video"), (r"شهادات|تجارب|مراجع", "testimonial review"),
    # going back to an earlier subject
    (r"نعود|لنعد|نرجع|العود[هة] (ال|ل)", "back to"), (r"\bالاول|\bاول\b", "first"),
]
_COMPILED = [(re.compile(pattern), words) for pattern, words in GLOSSES]


def fold(text: str) -> str:
    return _DIACRITICS.sub("", text).translate(_FOLD)


def with_glosses(text: str) -> str:
    """The text plus English words for the Arabic terms in it (unchanged if it has no Arabic)."""
    if not _ARABIC.search(text):
        return text
    folded = fold(text)
    words = [english for pattern, english in _COMPILED if pattern.search(folded)]
    return text + (" | " + " ".join(words) if words else "")
