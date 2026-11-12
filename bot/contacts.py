"""Last checks on a reply before it is sent: no foreign links, no contact details.

Done in code, not left to the model: a user may ask the bot to promote a
look-alike payment site, or to hand out someone's email or phone number. None
of that is on the 7 pages, so the reply must never carry it, whatever the
model writes.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

ALLOWED_HOSTS = ("placidway.com", "988lifeline.org", "findahelpline.com")
REPLACEMENT = "that address"

# A full URL, a www. address, or a bare domain such as "pay-here.co".
_LINK = re.compile(
    r"https?://[^\s<>()\[\]\"'`]*|www\.[^\s<>()\[\]\"'`]*"
    r"|\b(?:[a-z0-9-]+\.)+(?:com|co|net|org|io|info|biz|mx|ly|me|app|dev|xyz|site|online|link|ru|cn)\b"
    r"(?:/[^\s<>()\[\]\"'`]*)?",
    re.I,
)
# A look-alike of the brand written without its ending, such as "placidway-billing".
_LOOKALIKE = re.compile(r"\bplacidway[-_][a-z0-9][a-z0-9-]*")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"\+?(?:\d{1,3}[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b")
# Banking terms never appear on the pages; a list of them becomes "bank details".
_BANK_TERM = r"(?:an? )?(?:IBAN|SWIFT|BIC|routing)(?: (?:numbers?|codes?))?"
_BANK_TERMS = re.compile(rf"{_BANK_TERM}(?:(?:,| or| and|/)\s*{_BANK_TERM})*", re.I)


def _allowed(link: str) -> bool:
    url = link if re.match(r"https?://", link, re.I) else "http://" + link
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


def _replace_link(match: re.Match) -> str:
    link = match.group(0).rstrip(".,;:!?")
    return match.group(0) if _allowed(link) else REPLACEMENT + match.group(0)[len(link):]


def scrub(text: str) -> str:
    """Remove foreign links, brand look-alikes, emails, phone numbers and banking terms."""
    text = _EMAIL.sub("(contact details are not shared)", text).replace("@", " at ")
    text = _LINK.sub(_replace_link, text)
    text = _LOOKALIKE.sub(REPLACEMENT, text)
    text = _PHONE.sub("(contact details are not shared)", text)
    return _BANK_TERMS.sub("bank details", text)
