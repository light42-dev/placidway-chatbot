"""Guess which language a text is written in, for the few sentences the bot adds in code."""
from __future__ import annotations

import re

LANGUAGES = ("en", "es", "fr", "ar")

_COMMON_WORDS = {
    "es": {"el", "la", "los", "de", "que", "y", "es", "para", "con", "no", "por", "precio"},
    "fr": {"le", "la", "les", "de", "des", "et", "est", "pour", "avec", "pas", "je", "vous"},
    "en": {"the", "and", "is", "of", "to", "for", "that", "with", "i", "you", "can", "price"},
}


def detect(text: str) -> str:
    """One of LANGUAGES: Arabic by its letters, otherwise by counting very common words. Defaults to English."""
    letters = [c for c in text if c.isalpha()]
    if letters and sum("\u0600" <= c <= "\u06ff" for c in letters) / len(letters) > 0.4:
        return "ar"
    words = re.findall(r"[a-záéíóúñàâçèêëîïôûù]+", text.lower())
    counts = {language: sum(word in common for word in words) for language, common in _COMMON_WORDS.items()}
    return max(counts, key=counts.get) if any(counts.values()) else "en"
