"""Write the run's transcripts and numbers to reports/."""
from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from .consistency import compare_runs, similarity
from .runner import ConversationResult
from .scenarios import get_persona


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, round(pct / 100 * (len(ordered) - 1))))
    return ordered[rank]


def summarize(conversations: list[ConversationResult]) -> dict:
    turns = [t for c in conversations for t in c.turns if t.skipped is None]
    answered = [t for t in turns if t.answered]
    latencies = [t.latency_s for t in answered if t.latency_s is not None]
    tokens = [t.total_tokens for t in answered if t.total_tokens is not None]
    summary = {
        "conversations": len(conversations),
        "turns_sent": len(turns),
        "turns_passed": sum(t.passed for t in turns),
        "turns_failed": sum(not t.passed for t in turns),
        "turns_without_usage": sum(t.total_tokens is None for t in answered),
    }
    if latencies:
        summary["latency_s"] = {"median": round(statistics.median(latencies), 2),
                                "p95": round(percentile(latencies, 95), 2),
                                "max": round(max(latencies), 2)}
    if tokens:
        summary["tokens_per_reply"] = {"median": int(statistics.median(tokens)), "max": max(tokens),
                                       "total": sum(tokens)}
    return summary


def _by_persona(conversations: list[ConversationResult]) -> dict[str, list[ConversationResult]]:
    grouped: dict[str, list[ConversationResult]] = {}
    for conversation in sorted(conversations, key=lambda c: (c.persona_id, c.run)):
        grouped.setdefault(conversation.persona_id, []).append(conversation)
    return grouped


def write_reports(conversations: list[ConversationResult], directory: Path, settings: dict) -> Path:
    """Write report-<time>.json and a readable transcript; return the transcript path."""
    directory.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    summary = summarize(conversations)
    grouped = _by_persona(conversations)

    consistency = {}
    for persona_id, runs in grouped.items():
        if len(runs) > 1:
            score = similarity(runs)
            consistency[persona_id] = {"differences": compare_runs(runs),
                                       "lowest_text_similarity": None if score is None else round(score, 2)}

    payload = {"created": stamp, "settings": settings, "summary": summary,
               "consistency": consistency, "conversations": [c.to_dict() for c in conversations]}
    (directory / f"report-{stamp}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [f"# Bot test transcript, {stamp}", "", "```json",
             json.dumps({"settings": settings, "summary": summary}, indent=2), "```", ""]
    for persona_id, runs in grouped.items():
        persona = get_persona(persona_id)
        lines += [f"## {persona.id} {persona.name}: {persona.label}", ""]
        for difference in consistency.get(persona_id, {}).get("differences", []):
            lines.append(f"- INCONSISTENT: {difference}")
        for conversation in runs:
            lines += ["", f"### Run {conversation.run}", ""]
            for turn in conversation.turns:
                tags = f" [{', '.join(turn.tags)}]" if turn.tags else ""
                lines.append(f"**{turn.index + 1}. {turn.turn_id}{tags}**")
                lines.append(f"- User: {turn.user}")
                if turn.skipped:
                    lines += [f"- Skipped: {turn.skipped}", ""]
                    continue
                if turn.burst:
                    lines.append(f"- Burst: {turn.burst}")
                else:
                    reply = turn.reply.replace("\n", " ") or f"(no answer: {turn.error or turn.status})"
                    latency = "n/a" if turn.latency_s is None else f"{turn.latency_s:.2f}s"
                    lines.append(f"- Bot (HTTP {turn.status}, {latency}, {turn.total_tokens} tokens): {reply}")
                for check in turn.failures:
                    lines.append(f"- FAIL {check['name']}: {check['detail']}")
                lines.append("")
    transcript = directory / f"transcript-{stamp}.md"
    transcript.write_text("\n".join(lines), encoding="utf-8")
    return transcript
