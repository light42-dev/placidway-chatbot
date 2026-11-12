"""Find the passages most relevant to a conversation.

The index (data/index.json) is small, about 180 passages, so plain BM25
keyword scoring in memory is enough: no embeddings and no extra services.

Three additions make real questions work:
- synonyms: "how much" should find a passage that says "Cost ... $18,995",
  so related words are grouped (SYNONYMS) and money amounts become one token;
- earlier user messages also count as query words, at a lower weight, so
  "and the inpatient one?" still finds the package that was being discussed;
- passages from the page under discussion (the focus page) get a bonus.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

from .config import CONTEXT_CHARS, ROOT
from .pages import PAGES

K1, B = 1.5, 0.75           # the usual BM25 constants
EARLIER_WEIGHT = 0.4        # weight of the previous user message; halves for each one before it
SYNONYM_WEIGHT = 0.6        # weight of a word added through SYNONYMS, relative to the word that triggered it
FOCUS_BONUS = 3.0           # multiplier for passages of the page under discussion
MONEY = "_money"            # stands for any dollar amount, in passages and in questions

# Words that mean roughly the same thing to a visitor. A question containing
# one word of a group also searches for the others.
SYNONYMS = [
    {"cost", "price", "much", "pay", "fee", "total", "expensive", "afford", "program", MONEY},
    {"include", "cover", "exclude", "extra", "additional"},
    {"inpatient", "overnight", "stay", "room", "hotel", "accommodation", "board"},
    {"outpatient", "daily"},
    {"flight", "fly", "airport", "plane", "travel", "transport"},
    {"meal", "food", "eat", "nutrition", "nutritional"},
    {"video", "testimonial", "story", "review", "watch"},
    {"doctor", "physician", "staff", "team"},
]

STOPWORDS = set("""a an and are as at be but by can do does for from how i if in is it its me my of on or
so that the their them there this to was we what when where which who will with you your about one""".split())


@dataclass(frozen=True)
class Passage:
    page: str     # page key from bot/pages.py
    text: str


def stem(word: str) -> str:
    """Crude suffix stripping so 'include', 'includes', 'included' and 'including' are one term."""
    if len(word) > 4:
        for suffix in ("ing", "ed", "es", "s"):
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                word = word[:-len(suffix)]
                break
        if word.endswith("e"):
            word = word[:-1]
    return word


def tokenize(text: str) -> list[str]:
    """Lowercase stemmed words without stopwords; hyphens are dropped ('in-patient' -> 'inpatient')."""
    text = text.lower().replace("-", "")
    tokens = [stem(word) for word in re.findall(r"[a-z0-9]+", text) if word not in STOPWORDS]
    if re.search(r"\$\s?\d|\d\s?k\b|\busd\b|\bdollar", text):
        tokens.append(MONEY)
    return tokens


SYNONYM_STEMS = [{word if word == MONEY else stem(word) for word in group} for group in SYNONYMS]


def expand(terms: set[str]) -> dict[str, float]:
    """The terms at weight 1, plus their synonyms at a lower weight."""
    weights = {term: 1.0 for term in terms}
    for group in SYNONYM_STEMS:
        if group & terms:
            for word in group - terms:
                weights[word] = SYNONYM_WEIGHT
    return weights


def find_focus_page(user_messages: list[str], last_cited: str | None) -> str | None:
    """The page the conversation is about: the newest topic word a user wrote, else the page cited last."""
    for message in reversed(user_messages):
        lowered = message.lower()
        for page in PAGES:
            if any(re.search(rf"\b{re.escape(topic)}", lowered) for topic in page.topics):
                return page.key
    return last_cited


class Index:
    def __init__(self, passages: list[Passage]):
        self.passages = passages
        self.term_counts = [Counter(tokenize(p.text)) for p in passages]
        self.lengths = [sum(c.values()) for c in self.term_counts]
        self.average_length = sum(self.lengths) / max(len(passages), 1)
        document_frequency = Counter(term for counts in self.term_counts for term in counts)
        total = len(passages)
        self.idf = {term: math.log(1 + (total - df + 0.5) / (df + 0.5)) for term, df in document_frequency.items()}

    def _score(self, i: int, query: dict[str, float]) -> float:
        counts, length = self.term_counts[i], self.lengths[i]
        score = 0.0
        for term, weight in query.items():
            frequency = counts.get(term, 0)
            if frequency:
                norm = frequency + K1 * (1 - B + B * length / self.average_length)
                score += weight * self.idf[term] * frequency * (K1 + 1) / norm
        return score

    def search(self, user_messages: list[str], focus_page: str | None = None,
               budget_chars: int = CONTEXT_CHARS) -> list[Passage]:
        """Best passages for the newest user message, in ranked order, within the size budget."""
        query: dict[str, float] = {}
        weight = 1.0
        for message in reversed(user_messages):          # newest first
            for term, synonym_weight in expand(set(tokenize(message))).items():
                if term in self.idf:
                    query[term] = max(query.get(term, 0.0), weight * synonym_weight)
            weight = EARLIER_WEIGHT if weight == 1.0 else weight / 2

        scored = []
        for i, passage in enumerate(self.passages):
            score = self._score(i, query)
            if focus_page and passage.page == focus_page:
                score *= FOCUS_BONUS
            if score > 0:
                scored.append((score, i))
        scored.sort(key=lambda item: (-item[0], item[1]))

        chosen: list[Passage] = []
        used = 0
        for _, i in scored:
            passage = self.passages[i]
            if used + len(passage.text) > budget_chars:
                continue            # too big for what is left; a shorter one may still fit
            chosen.append(passage)
            used += len(passage.text)
        return chosen


@lru_cache(maxsize=1)
def load_index() -> Index:
    rows = json.loads((ROOT / "data" / "index.json").read_text(encoding="utf-8"))
    return Index([Passage(row["page"], row["text"]) for row in rows])
