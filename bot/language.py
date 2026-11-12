"""Guess which language a text is written in, for the few sentences the bot adds in code."""
from __future__ import annotations

import re

LANGUAGES = ("en", "es", "fr", "ar")

NAMES = {"en": "English", "es": "Spanish", "fr": "French", "ar": "Arabic"}

# English comes first so that a tie goes to English.
_COMMON_WORDS = {
    "en": {"the", "and", "is", "of", "to", "for", "that", "with", "i", "you", "can", "price", "it", "my",
           "what", "how", "do", "does", "are", "this", "in"},
    "es": {"el", "la", "los", "de", "que", "y", "es", "para", "con", "no", "por", "precio", "mi", "su", "un",
           "una", "se", "lo", "como", "hay", "tiene", "cuanto", "eso"},
    "fr": {"le", "la", "les", "de", "des", "et", "est", "pour", "avec", "pas", "je", "vous", "un", "une", "du",
           "que", "qui", "il", "ce", "dans"},
}
_ACCENTS = {"es": "ñ¿¡áíóú", "fr": "çèêàùœâîô"}       # letters that English text does not use


def detect(text: str, sure: bool = False) -> str:
    """One of LANGUAGES: Arabic by its letters, otherwise by counting very common words and accents.

    English when nothing points elsewhere, or on a tie. With `sure`, another
    language needs at least two signs, so one stray "no" or "la" is not enough.
    """
    letters = [c for c in text if c.isalpha()]
    if letters and sum("\u0600" <= c <= "\u06ff" for c in letters) / len(letters) > 0.4:
        return "ar"
    lowered = text.lower()
    words = re.findall(r"[a-záéíóúñàâçèêëîïôûùœ]+", lowered)
    counts = {language: sum(word in common for word in words) for language, common in _COMMON_WORDS.items()}
    for language, accents in _ACCENTS.items():
        counts[language] += any(letter in lowered for letter in accents)
    best = max(counts, key=counts.get)
    return "en" if sure and counts[best] < 2 else best
