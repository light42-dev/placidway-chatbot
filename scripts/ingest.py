"""Re-crawl the 7 PlacidWay pages and rebuild the index.

    python scripts/ingest.py

Writes data/pages/<key>.txt (the readable text of each page) and
data/index.json (that text cut into passages). Both are committed, because
the hosting target has no disk to build them on at run time.

Only the 7 URLs in bot/pages.py are fetched: robots.txt is respected, the
User-Agent says what this is, and requests are one second apart.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bot.pages import BASE, PAGES  # noqa: E402

USER_AGENT = "placidway-bot-ingest/1.0"
DATA = ROOT / "data"
PASSAGE_CHARS = 1200          # target size of one passage

SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "header", "footer", "form", "iframe", "select", "button"}
VOID_TAGS = {"br", "hr", "img", "input", "meta", "link", "source", "area", "base", "col", "embed", "wbr"}
HEADING_TAGS = {"h1", "h2", "h3", "h4"}
BLOCK_TAGS = {"p", "div", "li", "tr", "br", "section", "article", "table", "ul", "ol", "dd", "dt"} | HEADING_TAGS


class TextExtractor(HTMLParser):
    """Collects the visible text inside <main>, one line per block, headings marked with '#'."""

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []
        self._buffer: list[str] = []
        self._in_main = 0
        self._skip = 0
        self._heading = False

    def _flush(self) -> None:
        text = re.sub(r"\s+", " ", "".join(self._buffer)).strip()
        self._buffer = []
        if text:
            self.lines.append(("# " if self._heading else "") + text)

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self._in_main += 1
        if tag in VOID_TAGS and tag != "br":
            return
        if tag in SKIP_TAGS:
            self._skip += 1
        if tag in BLOCK_TAGS:
            self._flush()
            self._heading = tag in HEADING_TAGS
        if tag in ("td", "th"):
            self._buffer.append(" | ")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self._skip:
            self._skip -= 1
        if tag in BLOCK_TAGS:
            self._flush()
            self._heading = False
        if tag == "main" and self._in_main:
            self._in_main -= 1

    def handle_data(self, data):
        if self._in_main and not self._skip:
            self._buffer.append(data)


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


# The price shown on a package card, for example "Price starting from $24,000".
CARD_PRICE = re.compile(r"^Price starting from \$[\d,]+$")


def attach_card_prices(lines: list[str]) -> list[str]:
    """Move each package card's price below the card's own title.

    In the HTML of the comparison page's package cards the price comes before
    the title. Read top to bottom, each price would then sit under the card
    before it and be given to the wrong clinic. A price line directly
    followed by a heading therefore changes places with that heading.
    """
    lines = list(lines)
    for i in range(len(lines) - 1):
        if CARD_PRICE.match(lines[i]) and lines[i + 1].startswith("# "):
            lines[i], lines[i + 1] = lines[i + 1], lines[i]
    return lines


def extract_text(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    parser.close()
    lines: list[str] = []
    for line in parser.lines:
        if not lines or line != lines[-1]:      # drop immediate repeats
            lines.append(line)
    return "\n".join(attach_card_prices(lines))


def split_passages(text: str) -> list[str]:
    """Cut at headings first, then at line breaks once a passage is long enough."""
    passages: list[str] = []
    current: list[str] = []
    size = 0
    for line in text.splitlines():
        starts_section = line.startswith("# ") and size > PASSAGE_CHARS // 3
        if current and (starts_section or size + len(line) > PASSAGE_CHARS):
            passages.append("\n".join(current))
            current, size = [], 0
        current.append(line)
        size += len(line) + 1
    if current:
        passages.append("\n".join(current))
    return passages


def main() -> int:
    robots = urllib.robotparser.RobotFileParser()
    robots.parse(fetch(f"{BASE}/robots.txt").splitlines())

    (DATA / "pages").mkdir(parents=True, exist_ok=True)
    index: list[dict] = []
    failed: list[str] = []
    for page in PAGES:
        time.sleep(1)
        if not robots.can_fetch(USER_AGENT, page.url):
            print(f"skipped (robots.txt): {page.url}")
            failed.append(page.key)
            continue
        try:
            text = extract_text(fetch(page.url))
        except Exception as exc:
            print(f"failed: {page.url}: {type(exc).__name__}: {exc}")
            failed.append(page.key)
            continue
        if len(text) < 200:
            print(f"failed: {page.url}: almost no text found")
            failed.append(page.key)
            continue
        (DATA / "pages" / f"{page.key}.txt").write_text(text + "\n", encoding="utf-8")
        passages = split_passages(text)
        index += [{"page": page.key, "n": n, "text": passage} for n, passage in enumerate(passages)]
        print(f"ok: {page.key}: {len(text)} characters, {len(passages)} passages")

    if failed:
        # Keep the old index rather than ship one with pages missing.
        print(f"index NOT rewritten; pages missing: {', '.join(failed)}")
        return 1
    (DATA / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(index)} passages to {DATA / 'index.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
