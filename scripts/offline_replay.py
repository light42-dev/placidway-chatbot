"""Play every persona through the bot with a stand-in model, at no API cost.

    python scripts/offline_replay.py            # all personas
    python scripts/offline_replay.py T01 E03    # some

The stand-in "model" answers each scripted message with that turn's reference
reply from the persona file. So this does NOT show what a real model would
say. It shows two things a live run cannot separate:

- retrieval: is a passage from the page the reference cites actually retrieved?
- the code after the model: do the checks in bot/guards and the citation step
  leave a correct reply correct?

It also prints the estimated prompt size per turn (about 4 characters per token).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bot import chat, web  # noqa: E402
from bot.llm import Completion  # noqa: E402
from bot.pages import PAGES  # noqa: E402
from botsuite.client import BotReply, parse_reply  # noqa: E402
from botsuite.runner import Runner  # noqa: E402
from botsuite.scenarios import load_personas  # noqa: E402

URL = re.compile(r"https?://\S+")


class StandInModel:
    """Replaces bot.llm.complete: returns the reference reply for the newest user message."""

    def __init__(self, personas):
        self.references = {turn.user: turn.reference for p in personas for turn in p.turns}
        self.prompt_chars: list[int] = []
        self.retrieval_misses: list[str] = []

    def __call__(self, system: str, messages: list[dict]) -> Completion:
        self.prompt_chars.append(len(system) + sum(len(m["content"]) for m in messages))
        question = messages[-1]["content"]
        reference = self.references.get(question, "I don't know; PlacidWay's pages don't list it.")
        cited = [page for page in PAGES if any(page.url in url for url in URL.findall(reference))]
        used = []
        for page in cited:
            found = re.search(rf"\[(\d+)\] From: {re.escape(page.title)}\n", system)
            if found:
                used.append(found.group(1))
            else:
                self.retrieval_misses.append(f"{question[:50]!r}: no passage from {page.key}")
        text = URL.sub("", reference).replace("Source:", "").strip()
        tokens = self.prompt_chars[-1] // 4
        return Completion(f"{text}\nUSED: {', '.join(used) or 'none'}", tokens, len(text) // 4, "stand-in")


class InProcessClient:
    """Stands in for botsuite.client.BotClient: calls the bot's request handler directly."""

    requests_sent = 0

    def send(self, messages: list[dict], session_id: str, throttle: bool = True) -> BotReply:
        import json
        self.requests_sent += 1
        status, body = web.handle_chat(json.dumps({"session_id": session_id, "messages": messages}).encode())
        answer, sources, total, model = parse_reply(body)
        return BotReply(status=status, answer=answer, sources=sources, total_tokens=total, model=model)


def main(wanted: list[str]) -> int:
    personas = [p for p in load_personas() if not wanted or p.id in wanted]
    model = StandInModel(load_personas())
    chat.complete = model
    web._limiter.limit = 10**9          # the replay sends requests back to back
    failed = 0
    for persona in personas:
        before = len(model.prompt_chars)
        result = Runner(InProcessClient()).run_conversation(persona, run=1)
        sizes = [chars // 4 for chars in model.prompt_chars[before:]]
        bad = [t for t in result.turns if not t.skipped and not t.passed]
        failed += len(bad)
        print(f"{persona.id}: {len(result.turns) - len(bad)}/{len(result.turns)} turns ok, "
              f"largest prompt about {max(sizes, default=0)} tokens")
        for turn in bad:
            reasons = "; ".join(f"{c['name']}: {c['detail']}" for c in turn.failures)
            print(f"   {turn.turn_id}: {reasons}\n      reply: {turn.reply[:200]!r}")
    for miss in model.retrieval_misses:
        print(f"retrieval miss  {miss}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
