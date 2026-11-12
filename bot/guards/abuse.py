"""Protection against scrapers and quota burners, done in code rather than left to the model.

- Requests to flood the output ("repeat X 100,000 times") or to extract data in
  bulk ("every price for all 2,500 clinics as JSON") get a fixed refusal with no
  model call, so they cost no quota and can never produce a huge reply.
- A per-client rate limit answers HTTP 429 to rapid-fire requests.
- A short-lived cache answers an identical conversation sent again within a few
  seconds without a second model call.
"""
from __future__ import annotations

import json
import re
import threading
import time
from collections import OrderedDict, defaultdict, deque

FLOOD_MIN_COUNT = 50        # "say it twice" is harmless; "say it 100 times" is flooding
BULK_MIN_COUNT = 100        # "all 2,500 clinics" is a directory, not a question

_COUNT_WORDS = {"hundred": 100, "hundreds": 100, "thousand": 1000, "thousands": 1000,
                "million": 10**6, "millions": 10**6, "billion": 10**9, "billions": 10**9}
_NUMBER = r"(\d[\d,.]*\s?(?:k|m)?\b|hundreds?|thousands?|millions?|billions?)"

_FLOOD_VERB = re.compile(r"\b(repeat|say|write|print|output|type|spam|echo|copy|generate|produce|send|give"
                         r"|repite|repetir|escribe|escribir|imprime|di)\b", re.I)
_FLOOD_COUNT = re.compile(_NUMBER + r"[\s-]*(times|copies|repetitions|lines|words?|characters|chars|tokens|pages|veces|copias|palabras|l[ií]neas)\b"
                          r"|\bx\s?" + _NUMBER, re.I)
_FLOOD_ENDLESS = re.compile(r"\b(forever|infinitely|endlessly|nonstop|non-stop|indefinitely)\b", re.I)

_BULK_SCOPE = re.compile(r"\b(all|every|each|entire|whole|full|complete)\b", re.I)
_BULK_FORMAT = re.compile(r"\b(json|csv|xml|sql|yaml|excel|spreadsheet)\b", re.I)
_BULK_VERB = re.compile(r"\b(dump|scrape|crawl|export|extract)\b", re.I)
_BULK_THINGS = re.compile(_NUMBER + r"\s+(\w+\s+)?(clinics|hospitals|providers|centers|centres|doctors"
                          r"|listings|packages|prices|treatments)\b", re.I)

FLOOD_REPLY = ("I can't do that. I can only answer questions about ITC (Immunity Therapy Center) "
               "from PlacidWay's pages, for example its treatment programs and listed prices.")
BULK_REPLY = ("I can't export data in bulk. I can only answer questions from a few PlacidWay pages about "
              "ITC (Immunity Therapy Center) and its listed prices, not PlacidWay's whole clinic directory. "
              "Ask me about a specific ITC program or price, or request a free quote from PlacidWay.")


def _count(text: str) -> int:
    """The number a match like '100,000', '100k', '1 million' or 'thousands' stands for."""
    text = text.lower().strip()
    if text in _COUNT_WORDS:
        return _COUNT_WORDS[text]
    multiplier = 1000 if text.endswith("k") else 10**6 if text.endswith("m") else 1
    digits = re.sub(r"[^\d.]", "", text.rstrip("km").replace(",", ""))
    try:
        return int(float(digits) * multiplier)
    except ValueError:
        return 0


def _is_flood(text: str) -> bool:
    if not _FLOOD_VERB.search(text):
        return False
    if _FLOOD_ENDLESS.search(text):
        return True
    return any(_count(m.group(1) or m.group(3) or "") >= FLOOD_MIN_COUNT for m in _FLOOD_COUNT.finditer(text))


def _is_bulk(text: str) -> bool:
    many = any(_count(m.group(1)) >= BULK_MIN_COUNT for m in _BULK_THINGS.finditer(text))
    scoped = bool(_BULK_SCOPE.search(text))
    return (many and scoped) or (scoped and bool(_BULK_FORMAT.search(text) or _BULK_VERB.search(text)))


def refusal_for(text: str) -> str | None:
    """A fixed refusal if the message asks for flooding or bulk extraction, else None."""
    if _is_flood(text):
        return FLOOD_REPLY
    if _is_bulk(text):
        return BULK_REPLY
    return None


class RateLimiter:
    """Allow at most `limit` requests per client in any `window_s` seconds."""

    def __init__(self, limit: int, window_s: float):
        self.limit, self.window_s = limit, window_s
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, client: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[client]
            while hits and now - hits[0] > self.window_s:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True


class ReplyCache:
    """Remember recent replies by conversation, so identical repeats cost no model call."""

    def __init__(self, ttl_s: float, max_items: int = 128):
        self.ttl_s, self.max_items = ttl_s, max_items
        self._items: OrderedDict[str, tuple[float, dict]] = OrderedDict()
        self._lock = threading.Lock()

    @staticmethod
    def key(messages: list) -> str:
        return json.dumps(messages, sort_keys=True, ensure_ascii=False)

    def get(self, messages: list) -> dict | None:
        key = self.key(messages)
        with self._lock:
            item = self._items.get(key)
            if not item or time.monotonic() - item[0] > self.ttl_s:
                return None
            reply = dict(item[1])
        # A cached reply used no new tokens.
        reply["usage"] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        return reply

    def put(self, messages: list, reply: dict) -> None:
        with self._lock:
            self._items[self.key(messages)] = (time.monotonic(), reply)
            while len(self._items) > self.max_items:
                self._items.popitem(last=False)
