"""Compare repeated runs of the same conversation."""
from __future__ import annotations

from difflib import SequenceMatcher

from .checks import extract_amounts
from .runner import ConversationResult


def compare_runs(runs: list[ConversationResult], compare_amounts: bool = True) -> list[str]:
    """Return one line per turn whose runs disagree. Empty list = consistent.

    Two runs agree on a turn when the HTTP status is the same, every check
    has the same verdict, and (unless compare_amounts is off) the reply
    states the same set of dollar amounts. Wording is free to differ.
    """
    differences = []
    for turns in zip(*(r.turns for r in runs)):
        first = turns[0]
        if any(t.skipped or t.burst for t in turns):
            continue
        label = f"{first.persona_id} turn {first.index + 1} ({first.turn_id})"

        statuses = [t.status for t in turns]
        if len(set(statuses)) > 1:
            differences.append(f"{label}: HTTP status differs across runs: {statuses}")
            continue

        verdicts = [tuple((c["name"], c["passed"]) for c in t.checks) for t in turns]
        if len(set(verdicts)) > 1:
            flaky = sorted({name for v in verdicts for name, _ in v
                            if len({dict(w).get(name) for w in verdicts}) > 1})
            per_run = ["pass" if t.passed else "FAIL" for t in turns]
            differences.append(f"{label}: verdict differs across runs {per_run}; unstable checks: {', '.join(flaky)}")
            continue

        if compare_amounts:
            amounts = [frozenset(extract_amounts(t.reply)) for t in turns]
            if len(set(amounts)) > 1:
                shown = [sorted(a) for a in amounts]
                differences.append(f"{label}: dollar amounts differ across runs: {shown}")
    return differences


def similarity(runs: list[ConversationResult]) -> float | None:
    """Lowest text similarity (0-1) between run 1 and any other run, for the report."""
    scores = []
    for turns in zip(*(r.turns for r in runs)):
        if any(not t.answered for t in turns):
            continue
        scores += [SequenceMatcher(None, turns[0].reply, t.reply).ratio() for t in turns[1:]]
    return min(scores) if scores else None
